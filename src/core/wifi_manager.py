import asyncio
from typing import List, Optional
import subprocess
import logging
from .models import WiFiStatus, WiFiNetwork
import os
from src.utils.logger import setup_logger
from functools import partial

logger = setup_logger()

class WiFiManager:
    """Manages WiFi connections using NetworkManager"""
    
    def __init__(self, skip_verify: bool = False):
        """Initialize WiFi manager"""
        self.logger = logger
        self._skip_verify = skip_verify  # Store skip_verify flag
        self._interface = "wlan0"
        # Don't run verification in __init__, provide a separate method

    async def initialize(self):
        """Async initialization method"""
        if not os.getenv('SKIP_NM_CHECK') and not self._skip_verify:
            await self._verify_networkmanager()

    async def _verify_networkmanager(self) -> None:
        """Verify NetworkManager is running"""
        try:
            result = await self._run_command(['systemctl', 'is-active', 'NetworkManager'])
            if result.returncode != 0:
                raise RuntimeError("NetworkManager service is not active")
        except Exception as e:
            self.logger.error("NetworkManager verification failed: %s", str(e))
            raise RuntimeError("NetworkManager is not running") from e

    async def get_current_status(self) -> WiFiStatus:
        """Get current WiFi status"""
        try:
            # Get list of saved connections with basic info first
            saved_result = await self._run_command([
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
                                config_result = await self._run_command([
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
            result = await self._run_command([
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
                internet_check = await self._run_command([
                    'sudo', 'nmcli', 'networking', 'connectivity', 'check'
                ], capture_output=True, text=True, timeout=5)
                has_internet = internet_check.returncode == 0 and internet_check.stdout.strip() == 'full'

            # Create a mapping of SSIDs to connection names
            ssid_to_conn_name = {}
            if saved_result.returncode == 0:
                for line in saved_result.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 2 and ('wifi' in parts[1].lower() or '802-11-wireless' in parts[1].lower()):
                        conn_name = parts[0].strip()
                        ssid_to_conn_name[conn_name] = conn_name
                        if conn_name == 'preconfigured' and len(parts) >= 3:
                            try:
                                config_file = parts[2].strip()
                                config_result = await self._run_command([
                                    'sudo', 'cat', config_file
                                ], capture_output=True, text=True)
                                if config_result.returncode == 0:
                                    for config_line in config_result.stdout.split('\n'):
                                        if 'ssid=' in config_line.lower():
                                            ssid = config_line.split('=')[1].strip()
                                            ssid_to_conn_name[ssid] = conn_name
                                            self.logger.debug(f"Mapped SSID {ssid} to connection name {conn_name}")
                            except Exception as e:
                                self.logger.error(f"Error reading preconfigured network: {e}")

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

    async def _run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run system commands asynchronously"""
        try:
            # Create a partial function with the command and kwargs
            cmd_func = partial(subprocess.run, command, **kwargs)
            
            # Run in threadpool to avoid blocking
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, cmd_func)
            
            return result
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
        try:
            self.logger.debug(f"\n=== Starting connection process for SSID: {ssid} ===")
            
            # 1. Get current status to verify network exists
            self.logger.debug("1. Getting current network status...")
            status = await self.get_current_status()
            available_ssids = [net.ssid for net in status.available_networks]
            
            if ssid not in available_ssids:
                self.logger.error(f"Network {ssid} not found in scan results")
                return False
            
            # 2. Connect to network
            self.logger.debug("2. Connecting to network...")
            connect_cmd = ['sudo', 'nmcli', 'device', 'wifi', 'connect', ssid]
            if password:
                connect_cmd.extend(['password', password])
            
            result = await self._run_command(connect_cmd)
            if result.returncode != 0:
                self.logger.error(f"Failed to connect: {result.stderr}")
                await self._remove_connection(ssid)
                return False
            
            # 3. Verify connection
            self.logger.debug("3. Verifying connection...")
            verify_result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'
            ])
            
            self.logger.debug(f"Verification result: {verify_result.stdout}")
            
            # Check for "100" in the state output, which indicates connected
            if verify_result.returncode == 0 and 'GENERAL.STATE:100' in verify_result.stdout:
                self.logger.debug("Connection successful!")
                return True
            else:
                self.logger.error("Connection verification failed")
                await self._remove_connection(ssid)
                return False
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            await self._remove_connection(ssid)
            return False

    async def _remove_connection(self, ssid: str) -> bool:
        """Remove a network connection"""
        try:
            self.logger.debug(f"Removing connection for {ssid}")
            result = await self._run_command([
                'sudo', 'nmcli', 'connection', 'delete', ssid
            ])
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error removing connection: {e}")
            return False

    async def _parse_network_list(self, output: str, saved_networks: Optional[set] = None) -> List[WiFiNetwork]:
        """Parse nmcli output into WiFiNetwork objects"""
        networks = []
        
        if saved_networks is None:
            # Get saved networks if not provided
            saved_result = await self._run_command([
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

    async def _rescan_networks(self) -> bool:
        """Rescan for available networks"""
        try:
            self.logger.debug("Starting network scan...")
            # Request a new scan
            scan_result = await self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'rescan'
            ])
            if scan_result.returncode != 0:
                self.logger.error(f"Failed to initiate scan: {scan_result.stderr}")
                return False

            # Wait for scan to complete and get results
            for attempt in range(10):
                self.logger.debug(f"Device status (attempt {attempt + 1}/10): ")
                result = await self._run_command([
                    'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'
                ])
                
                if result.returncode == 0 and result.stdout.strip():
                    self.logger.debug(f"Scan completed successfully")
                    return True
                
                await asyncio.sleep(1)
            
            self.logger.error("Network rescan failed: ")
            return False
        except Exception as e:
            self.logger.error(f"Error during network scan: {e}")
            return False

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

    async def get_preconfigured_ssid(self) -> Optional[str]:
        """Get the SSID for the preconfigured connection"""
        try:
            config_file = '/etc/NetworkManager/system-connections/preconfigured.nmconnection'
            config_result = await self._run_command([
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
    async def _is_network_saved(self, ssid: str) -> bool:
        """Check if a network is already saved in NetworkManager"""
        try:
            result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'NAME', 'connection', 'show'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to check saved networks: {result.stderr}")
                return False
            
            saved_networks = result.stdout.strip().split('\n')
            self.logger.debug(f"Found saved networks: {saved_networks}")
            
            return ssid in saved_networks
            
        except Exception as e:
            self.logger.error(f"Error checking saved networks: {e}")
            return False
