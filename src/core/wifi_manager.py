import asyncio
from typing import List, Optional
import subprocess
import logging
from .models import WiFiStatus, WiFiNetwork, NetworkModeStatus, NetworkMode
import os
from src.utils.logger import setup_logger

logger = setup_logger()

class WiFiManager:
    """Manages WiFi connections using NetworkManager"""
    
    def __init__(self, skip_verify: bool = False):
        """Initialize WiFi manager"""
        self.logger = logger
        # Check both environment variable and skip_verify parameter
        if not os.getenv('SKIP_NM_CHECK') and not skip_verify:
            self._verify_networkmanager()
        self._interface = "wlan0"
        
    def _verify_networkmanager(self) -> None:
        """Verify NetworkManager is running"""
        try:
            result = self._run_command(['systemctl', 'is-active', 'NetworkManager'])
            if result.returncode != 0:
                raise RuntimeError("NetworkManager service is not active")
        except Exception as e:
            self.logger.error("NetworkManager verification failed: %s", str(e))
            raise RuntimeError("NetworkManager is not running") from e

    def get_current_status(self) -> WiFiStatus:
        """Get current WiFi status"""
        try:
            # Check if we're in AP mode first
            current_mode = self.get_operation_mode()
            is_ap_mode = current_mode.mode == NetworkMode.AP
            
            # Get list of saved connections with basic info first
            saved_result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'NAME,TYPE,FILENAME', 'connection', 'show'
            ], capture_output=True, text=True)
            
            self.logger.debug("\n=== Start Debug Output ===")
            self.logger.debug("1. Getting saved connections:")
            self.logger.debug(f"Command output: {saved_result.stdout}")
            
            # Track saved networks and their configuration files
            saved_networks = set()
            if saved_result.returncode == 0:
                for line in saved_result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split(':')
                    # Check for both 'wifi' and '802-11-wireless' in type field
                    if len(parts) >= 2 and ('wifi' in parts[1].lower() or '802-11-wireless' in parts[1].lower()):
                        conn_name = parts[0].strip()
                        saved_networks.add(conn_name)
                        
                        # Keep existing preconfigured network handling
                        if conn_name == 'preconfigured' and len(parts) >= 3:
                            try:
                                config_file = parts[2].strip()
                                config_result = self._run_command([
                                    'sudo', 'cat', config_file
                                ], capture_output=True, text=True)
                                if config_result.returncode == 0:
                                    for config_line in config_result.stdout.split('\n'):
                                        if 'ssid=' in config_line.lower():
                                            ssid = config_line.split('=')[1].strip()
                                            saved_networks.add(ssid)
                                            self.logger.debug(f"Added preconfigured SSID: {ssid}")
                            except Exception as e:
                                self.logger.error(f"Error reading preconfigured network: {e}")

            # Get current networks list
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list'
            ], capture_output=True, text=True, timeout=5)
            
            networks = []
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    try:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            ssid, signal, security, in_use = parts[:4]
                            if ssid:  # Skip empty SSIDs
                                is_saved = (
                                    ssid in saved_networks or 
                                    ssid.replace(" ", "") in saved_networks or
                                    in_use == '*'
                                )
                                networks.append(WiFiNetwork(
                                    ssid=ssid,
                                    signal_strength=int(signal),
                                    security=security if security != '' else None,
                                    in_use=(in_use == '*'),
                                    saved=is_saved
                                ))
                    except Exception as e:
                        self.logger.error(f"Error parsing network: {line} - {e}")

            # Aggregate networks with same SSID
            aggregated_networks = self._aggregate_networks(networks)
            aggregated_networks.sort(key=lambda x: x.signal_strength, reverse=True)

            # Handle AP mode status
            if is_ap_mode:
                return WiFiStatus(
                    ssid=current_mode.ap_ssid,
                    signal_strength=100,
                    is_connected=True,
                    has_internet=False,
                    available_networks=aggregated_networks
                )

            # Get current network
            current_network = next(
                (net for net in aggregated_networks if net.in_use),
                None
            )

            # Check internet connectivity
            has_internet = False
            if current_network:
                internet_check = self._run_command([
                    'sudo', 'nmcli', 'networking', 'connectivity', 'check'
                ], capture_output=True, text=True, timeout=5)
                has_internet = internet_check.returncode == 0 and internet_check.stdout.strip() == 'full'

            return WiFiStatus(
                ssid=current_network.ssid if current_network else None,
                signal_strength=current_network.signal_strength if current_network else None,
                is_connected=bool(current_network),
                has_internet=has_internet,
                available_networks=aggregated_networks
            )

        except Exception as e:
            self.logger.error(f"Error getting WiFi status: {str(e)}")
            return WiFiStatus()

    async def _scan_networks(self) -> List[WiFiNetwork]:
        """Scan for available networks"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list', '--rescan', 'yes'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Network scan failed: {result.stderr}")
                return []
            
            networks = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        ssid, signal, security, in_use = parts[:4]
                        if ssid:  # Skip empty SSIDs
                            networks.append(WiFiNetwork(
                                ssid=ssid,
                                signal_strength=int(signal),
                                security=security,
                                in_use=(in_use.strip() == '*')
                            ))
                except Exception as e:
                    self.logger.error(f"Error parsing network: {line} - {str(e)}")
            return networks
        except Exception as e:
            self.logger.error(f"Error scanning networks: {str(e)}")
            return []

    def _get_current_connection(self) -> Optional[WiFiNetwork]:
        """Get current WiFi connection details"""
        try:
            # Use iwconfig instead of nmcli for more reliable access
            output = self._run_command(["iwconfig", self._interface])
            
            if "ESSID:" in output:
                ssid = output.split('ESSID:"')[1].split('"')[0]
                if ssid:
                    # Get signal strength using iwconfig
                    quality = output.split("Quality=")[1].split(" ")[0]
                    level = int(quality.split("/")[0]) / int(quality.split("/")[1]) * 100
                    
                    return WiFiNetwork(
                        ssid=ssid,
                        signal_strength=int(level),
                        security="WPA2",  # Assume WPA2 as default
                        in_use=True
                    )
            return None
            
        except Exception as e:
            logger.error(f"Error getting current connection: {e}")
            return None

    def _check_internet_connection(self) -> bool:
        """Check if there's internet connectivity"""
        try:
            # Try ping instead of nmcli connectivity check
            result = self._run_command([
                "ping", "-c", "1", "-W", "2", "8.8.8.8"
            ])
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Internet check failed: {e}")
            return False

    def _run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a shell command and return the result"""
        # Ensure capture_output and text are set for consistent test behavior
        kwargs.setdefault('capture_output', True)
        kwargs.setdefault('text', True)
        return subprocess.run(command, **kwargs)

    async def connect_to_network(self, ssid: str, password: Optional[str] = None) -> bool:
        """Connect to a WiFi network"""
        was_in_ap_mode = False
        try:
            self.logger.debug(f"Received connection request for SSID: {ssid} with password: {'****' if password else '(none)'}")
            
            # Check if we're in AP mode
            ap_result = self._run_command(['sudo', 'systemctl', 'is-active', 'hostapd'], 
                                        capture_output=True, text=True)
            was_in_ap_mode = ap_result.returncode == 0 and ap_result.stdout.strip() == "active"
            
            if was_in_ap_mode:
                self.logger.debug("Currently in AP mode, disabling before connecting")
                result = self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'], 
                                         capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error("Failed to disable AP mode")
                    return False

            # Attempt connection
            connect_cmd = ['sudo', 'nmcli', 'device', 'wifi', 'connect', ssid]
            if password:
                connect_cmd.extend(['password', password])
            
            connect_result = self._run_command(connect_cmd, capture_output=True, text=True)
            
            if connect_result.returncode != 0:
                self.logger.error(f"Connection failed: {connect_result.stderr}")
                self._remove_connection(ssid)
                if was_in_ap_mode:
                    self._restore_ap_mode(NetworkModeStatus(mode=NetworkMode.AP))
                return False
            
            # Give NetworkManager time to update connection state
            await asyncio.sleep(1)
            
            # Verify connection
            verify_result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'
            ], capture_output=True, text=True)
            
            if verify_result.returncode != 0:
                self.logger.error("Connection verification failed")
                self._remove_connection(ssid)
                if was_in_ap_mode:
                    self._restore_ap_mode(NetworkModeStatus(mode=NetworkMode.AP))
                return False
            
            # Check for connected state (100)
            if not any('GENERAL.STATE:100' in line for line in verify_result.stdout.splitlines()):
                self.logger.error("Connection state verification failed")
                self._remove_connection(ssid)
                if was_in_ap_mode:
                    self._restore_ap_mode(NetworkModeStatus(mode=NetworkMode.AP))
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to network: {str(e)}")
            if was_in_ap_mode:
                self._restore_ap_mode(NetworkModeStatus(mode=NetworkMode.AP))
            return False

    def _restore_ap_mode(self, mode_status: NetworkModeStatus) -> None:
        """Restore AP mode"""
        try:
            result = self._run_command(['sudo', 'systemctl', 'start', 'hostapd'], 
                                     capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Failed to restore AP mode: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error restoring AP mode: {str(e)}")

    def _remove_connection(self, ssid: str) -> bool:
        """Remove a saved connection"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', 'connection', 'delete', ssid
            ], capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error removing connection: {str(e)}")
            return False

    def _parse_network_list(self, output: str, saved_networks: Optional[set] = None) -> List[WiFiNetwork]:
        """Parse nmcli output into WiFiNetwork objects"""
        networks = []
        
        if saved_networks is None:
            # Get saved networks if not provided
            saved_result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'NAME', 'connection', 'show'
            ], capture_output=True, text=True)
            saved_networks = set()
            if saved_result.returncode == 0:
                saved_networks = set(saved_result.stdout.strip().split('\n'))

        for line in output.strip().split('\n'):
            if not line:
                continue
            try:
                ssid, signal, security, in_use = line.split(':')
                if ssid:  # Skip empty SSIDs
                    networks.append(WiFiNetwork(
                        ssid=ssid,
                        signal_strength=int(signal),
                        security=security if security != '' else None,
                        in_use=(in_use == '*'),
                        saved=(ssid in saved_networks)
                    ))
            except Exception as e:
                self.logger.error(f"Error parsing network: {line} - {e}")
        return networks

    async def _rescan_networks(self) -> None:
        """Force a rescan of available networks"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'rescan'
            ], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                self.logger.error(f"Network rescan failed: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error during network rescan: {e}")

    def _aggregate_networks(self, networks: List[WiFiNetwork]) -> List[WiFiNetwork]:
        """Aggregate networks with the same SSID, keeping the strongest signal"""
        aggregated = {}
        for network in networks:
            if network.ssid not in aggregated:
                aggregated[network.ssid] = network
            else:
                # Update if signal is stronger or if current network is in use/saved
                existing = aggregated[network.ssid]
                if (network.signal_strength > existing.signal_strength or 
                    network.in_use or network.saved):
                    aggregated[network.ssid] = network
        
        return list(aggregated.values())

    def get_preconfigured_ssid(self) -> Optional[str]:
        """Get the SSID for the preconfigured connection"""
        try:
            config_file = '/etc/NetworkManager/system-connections/preconfigured.nmconnection'
            config_result = self._run_command([
                'sudo', 'cat', config_file
            ], capture_output=True, text=True)
            
            if config_result.returncode == 0:
                for line in config_result.stdout.split('\n'):
                    if 'ssid=' in line.lower():
                        ssid = line.split('=')[1].strip()
                        self.logger.debug(f"Preconfigured SSID: {ssid}")
                        return ssid
        except Exception as e:
            self.logger.error(f"Error reading preconfigured network: {e}")
        return None

    def get_operation_mode(self) -> NetworkModeStatus:
        """Get current network mode status"""
        try:
            ap_active = self._check_ap_mode_active()
            ip_address = self.get_ip_address()
            
            if ap_active:
                # Get AP configuration details
                ap_ssid = "RadioAP"  # Default or read from config
                ap_password = "password123"  # Default or read from config
                return NetworkModeStatus(
                    mode=NetworkMode.AP,
                    ip_address=ip_address,
                    ap_ssid=ap_ssid,
                    ap_password=ap_password
                )
            
            return NetworkModeStatus(
                mode=NetworkMode.DEFAULT,
                ip_address=ip_address
            )
        except Exception as e:
            self.logger.error(f"Error getting operation mode: {str(e)}")
            raise

    def _check_ap_mode_active(self) -> bool:
        """Check if AP mode is currently active"""
        try:
            result = self._run_command([
                'sudo', 'systemctl', 'is-active', 'hostapd'
            ], capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error checking AP mode: {str(e)}")
            return False

    def get_ip_address(self) -> Optional[str]:
        """Get current IP address of wlan0"""
        try:
            result = self._run_command([
                'ip', '-4', 'addr', 'show', 'wlan0'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                import re
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            self.logger.error(f"Error getting IP address: {str(e)}")
            return None

    def enable_ap_mode(self, ssid: str, password: str, ip: str = "192.168.4.1") -> bool:
        """Enable Access Point mode"""
        try:
            logger.info(f"Enabling AP mode with SSID: {ssid}, IP: {ip}")
            
            # Check if hostapd and dnsmasq are installed
            if not self._check_required_packages():
                logger.error("Required packages (hostapd, dnsmasq) are not installed")
                return False

            # Configure hostapd before stopping NetworkManager
            logger.debug("Creating hostapd configuration...")
            hostapd_conf = f"""
interface={self._interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
            # Ensure directory exists
            os.makedirs('/etc/hostapd', exist_ok=True)
            
            # Write configuration
            logger.debug("Writing hostapd configuration...")
            try:
                with open('/etc/hostapd/hostapd.conf', 'w') as f:
                    f.write(hostapd_conf)
            except Exception as e:
                logger.error(f"Failed to write hostapd configuration: {str(e)}")
                return False

            # Configure dnsmasq
            dnsmasq_conf = f"""
interface={self._interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""
            try:
                with open('/etc/dnsmasq.conf', 'w') as f:
                    f.write(dnsmasq_conf)
            except Exception as e:
                logger.error(f"Failed to write dnsmasq configuration: {str(e)}")
                return False

            # Now stop NetworkManager
            logger.debug("Stopping NetworkManager...")
            result = self._run_command(["sudo", "systemctl", "stop", "NetworkManager"])
            if result.returncode != 0:
                logger.error(f"Failed to stop NetworkManager: {result.stderr}")
                return False

            # Configure IP address
            logger.debug(f"Configuring IP address: {ip}")
            ip_result = self._run_command([
                "sudo", "ip", "addr", "add", f"{ip}/24", "dev", self._interface
            ])
            if ip_result.returncode != 0:
                logger.error(f"Failed to configure IP: {ip_result.stderr}")
                self._cleanup_ap_mode()
                return False

            # Start services
            for service in ['hostapd', 'dnsmasq']:
                logger.debug(f"Starting {service}...")
                result = self._run_command(["sudo", "systemctl", "start", service])
                if result.returncode != 0:
                    logger.error(f"Failed to start {service}: {result.stderr}")
                    self._cleanup_ap_mode()
                    return False

            logger.info("AP mode enabled successfully")
            return True

        except Exception as e:
            logger.error(f"Error enabling AP mode: {str(e)}")
            self._cleanup_ap_mode()
            return False

    def _check_required_packages(self) -> bool:
        """Check if required packages are installed"""
        for package in ['hostapd', 'dnsmasq']:
            result = self._run_command(['which', package])
            if result.returncode != 0:
                logger.error(f"Package {package} is not installed")
                return False
        return True

    def _cleanup_ap_mode(self):
        """Cleanup AP mode in case of failure"""
        try:
            logger.debug("Running AP mode cleanup...")
            
            # Stop services in reverse order
            for service in ['hostapd', 'dnsmasq']:
                logger.debug(f"Stopping {service}...")
                self._run_command(["sudo", "systemctl", "stop", service])
            
            # Remove IP address
            logger.debug("Removing IP configuration...")
            self._run_command([
                "sudo", "ip", "addr", "flush", "dev", self._interface
            ])
            
            # Restart NetworkManager
            logger.debug("Restarting NetworkManager...")
            self._run_command(["sudo", "systemctl", "restart", "NetworkManager"])
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def disable_ap_mode(self) -> bool:
        """Disable AP mode"""
        try:
            # Stop AP services
            self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'], 
                             capture_output=True, text=True)
            self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'], 
                             capture_output=True, text=True)
            
            # Restart NetworkManager
            result = self._run_command([
                'sudo', 'systemctl', 'restart', 'NetworkManager'
            ], capture_output=True, text=True)
            
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error disabling AP mode: {str(e)}")
            return False

    def _parse_scan_results(self, scan_output: str) -> List[WiFiNetwork]:
        """Parse nmcli scan results into WiFiNetwork objects"""
        networks = []
        for line in scan_output.strip().split('\n'):
            if not line:
                continue
            try:
                parts = line.split(':')
                if len(parts) >= 4:
                    ssid, signal, security, in_use = parts[:4]
                    networks.append(WiFiNetwork(
                        ssid=ssid,
                        signal_strength=int(signal),
                        security=security,
                        in_use=(in_use == '*')
                    ))
            except Exception as e:
                self.logger.error(f"Error parsing network: {line} - {str(e)}")
        return networks

    def _verify_connection(self) -> bool:
        """Verify if the connection was successful"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'
            ], capture_output=True, text=True)
            
            # Debug log the actual output
            self.logger.debug(f"Connection verification output: {result.stdout}")
            
            if result.returncode != 0:
                return False
            
            # Check for any line containing both '100' and 'connected'
            for line in result.stdout.splitlines():
                if '100' in line and 'connected' in line.lower():
                    return True
                
            return False
        except Exception as e:
            self.logger.error(f"Error verifying connection: {str(e)}")
            return False