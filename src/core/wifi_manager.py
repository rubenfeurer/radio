import asyncio
from typing import List, Optional
import subprocess
import logging
from .models import WiFiStatus, WiFiNetwork

logger = logging.getLogger(__name__)

class WiFiManager:
    """Manages WiFi connections using NetworkManager"""
    
    def __init__(self, skip_verify=False):
        self.logger = logging.getLogger(__name__)
        self._interface = "wlan0"
        if not skip_verify:
            self._verify_networkmanager()
        
    def _verify_networkmanager(self) -> None:
        """Verify NetworkManager is running and accessible"""
        try:
            result = self._run_command(['systemctl', 'is-active', 'NetworkManager'])
            if result.returncode != 0 or 'active' not in result.stdout:
                raise RuntimeError("NetworkManager service is not active")
        except Exception as e:
            self.logger.error(f"NetworkManager verification failed: {e}")
            raise RuntimeError("NetworkManager is not running") from e

    def get_current_status(self) -> WiFiStatus:
        """Get current WiFi status"""
        try:
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
                    parts = line.split(':')
                    # Check for both 'wifi' and '802-11-wireless' in type field
                    if len(parts) >= 2 and ('wifi' in parts[1].lower() or '802-11-wireless' in parts[1].lower()):
                        conn_name = parts[0].strip()
                        saved_networks.add(conn_name)
                        
                        # If it's a preconfigured connection, get the SSID from the config file
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
                        
                        self.logger.debug(f"Added saved connection: {conn_name}")

            self.logger.debug(f"\n2. Final saved_networks set: {saved_networks}")

            # Get current networks
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to get WiFi status: {result.stderr}")
                return WiFiStatus()

            self.logger.debug("\n3. Getting available networks:")
            self.logger.debug(f"Command output: {result.stdout}")
            
            networks = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    ssid, signal, security, in_use = line.split(':')
                    if ssid:  # Skip empty SSIDs
                        is_saved = (
                            ssid in saved_networks or 
                            ssid.replace(" ", "") in saved_networks or
                            in_use == '*'  # Always mark currently connected network as saved
                        )
                        
                        self.logger.debug(f"\nProcessing network: {ssid}")
                        self.logger.debug(f"  - In saved_networks: {ssid in saved_networks}")
                        self.logger.debug(f"  - Without spaces: {ssid.replace(' ', '') in saved_networks}")
                        self.logger.debug(f"  - In use: {in_use == '*'}")
                        self.logger.debug(f"  - Final saved status: {is_saved}")
                        
                        networks.append(WiFiNetwork(
                            ssid=ssid,
                            signal_strength=int(signal),
                            security=security if security != '' else None,
                            in_use=(in_use == '*'),
                            saved=is_saved
                        ))
                except Exception as e:
                    self.logger.error(f"Error parsing network: {line} - {e}")

            self.logger.debug("\n=== End Debug Output ===")

            # Aggregate networks with same SSID
            aggregated_networks = self._aggregate_networks(networks)
            
            # Sort networks by signal strength
            aggregated_networks.sort(key=lambda x: x.signal_strength, reverse=True)

            # Get current network from aggregated list
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
            self.logger.error(f"Error getting WiFi status: {str(e)}", exc_info=True)
            return WiFiStatus()

    async def _scan_networks(self) -> List[WiFiNetwork]:
        """Scan for available networks"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list'
            ], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                self.logger.error(f"Network scan failed: {result.stderr}")
                return []
            return self._parse_network_list(result.stdout)
        except Exception as e:
            self.logger.error(f"Error scanning networks: {e}")
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
        default_kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': 5
        }
        kwargs = {**default_kwargs, **kwargs}
        try:
            return subprocess.run(command, **kwargs)
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout='',
                stderr='Command timed out'
            )
        except Exception as e:
            self.logger.error(f"Command failed: {' '.join(command)} - {e}")
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout='',
                stderr=str(e)
            )

    async def connect_to_network(self, ssid: str, password: Optional[str] = None) -> bool:
        """Connect to a WiFi network"""
        try:
            self.logger.debug(f"Attempting to connect to network: {ssid}")
            
            # Force a rescan first
            await self._rescan_networks()
            
            # Check if network is saved
            saved_result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'NAME', 'connection', 'show'
            ], capture_output=True, text=True)
            is_saved = saved_result.returncode == 0 and ssid in saved_result.stdout
            self.logger.debug(f"Network is saved: {is_saved}")

            # Get available networks to verify the network exists
            networks = await self._scan_networks()
            self.logger.debug(f"Found networks: {[net.ssid for net in networks]}")
            
            if not any(net.ssid == ssid for net in networks):
                self.logger.error(f"Network {ssid} not found")
                return False

            # Connect command varies based on whether network is saved
            if is_saved:
                self.logger.debug("Using saved network connection")
                result = self._run_command([
                    'sudo', 'nmcli', 'connection', 'up', ssid
                ], capture_output=True, text=True, timeout=30)
            else:
                self.logger.debug("Creating new network connection")
                if not password:
                    self.logger.error("Password required for unsaved network")
                    return False
                    
                result = self._run_command([
                    'sudo', 'nmcli', 'device', 'wifi', 'connect', ssid,
                    'password', password
                ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to connect to network: {result.stderr}")
                # Remove the failed connection if it was newly added
                if not is_saved:
                    self._remove_connection(ssid)
                return False
            
            # Verify connection was successful
            verify_result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'
            ], capture_output=True, text=True)
            
            success = verify_result.returncode == 0 and '100 (connected)' in verify_result.stdout
            self.logger.debug(f"Connection verification result: {success}")
            
            # If verification failed, remove the connection
            if not success and not is_saved:
                self._remove_connection(ssid)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error connecting to network: {str(e)}", exc_info=True)
            return False

    def _remove_connection(self, ssid: str) -> None:
        """Remove a saved connection"""
        try:
            self.logger.debug(f"Removing failed connection: {ssid}")
            result = self._run_command([
                'sudo', 'nmcli', 'connection', 'delete', ssid
            ], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Failed to remove connection: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error removing connection: {e}")

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