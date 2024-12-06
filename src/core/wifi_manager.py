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
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to get WiFi status: {result.stderr}")
                return WiFiStatus()

            networks = self._parse_network_list(result.stdout)
            current_network = next(
                (net for net in networks if net.in_use), 
                None
            )
            
            # Check internet connectivity if we have a connection
            has_internet = False
            if current_network:
                internet_check = self._run_command([
                    'sudo', 'nmcli', 'networking', 'connectivity', 'check'
                ], capture_output=True, text=True, timeout=5)
                has_internet = internet_check.stdout.strip() == 'full'

            return WiFiStatus(
                ssid=current_network.ssid if current_network else None,
                signal_strength=current_network.signal_strength if current_network else None,
                is_connected=bool(current_network),
                has_internet=has_internet,
                available_networks=networks
            )
            
        except Exception as e:
            self.logger.error(f"Error getting current connection: {e}")
            return WiFiStatus()

    def _scan_networks(self) -> List[WiFiNetwork]:
        """Scan for available WiFi networks"""
        try:
            # Force a new scan
            self._run_command(["nmcli", "device", "wifi", "rescan"])
            
            # Get scan results
            output = self._run_command([
                "nmcli", "-t", "-f",
                "SSID,SIGNAL,SECURITY,IN-USE",
                "device", "wifi", "list"
            ])
            
            networks = []
            for line in output.splitlines():
                if line:
                    parts = line.split(':')
                    if len(parts) >= 4:  # Ensure we have all required parts
                        ssid, signal, security, in_use = parts[:4]
                        if ssid:  # Skip empty SSIDs
                            networks.append(WiFiNetwork(
                                ssid=ssid,
                                signal_strength=int(signal),
                                security=security,
                                in_use=(in_use == '*' or in_use == 'yes')
                            ))
            
            return networks
            
        except Exception as e:
            logger.error(f"Error scanning networks: {e}")
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

    async def connect_to_network(self, ssid: str, password: str) -> bool:
        """Connect to a WiFi network"""
        try:
            # Force a rescan
            result = self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'rescan'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                self.logger.error(f"Network rescan failed: {result.stderr}")
                return False

            # Check if network is available
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list'
            ], capture_output=True, text=True, timeout=5)
            
            networks = self._parse_network_list(result.stdout)
            if not any(n.ssid == ssid for n in networks):
                self.logger.error(f"Network {ssid} not found in scan results")
                return False
            
            # Attempt connection
            result = self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'connect', ssid,
                'password', password
            ], capture_output=True, text=True, timeout=30)  # Longer timeout for connection
            
            if result.returncode != 0:
                self.logger.error(f"Failed to connect to network: {result.stderr}")
                return False
            
            # Verify connection
            status = self.get_current_status()
            return status.ssid == ssid and status.is_connected
            
        except Exception as e:
            self.logger.error(f"Error connecting to network: {e}")
            return False

    def _parse_network_list(self, output: str) -> List[WiFiNetwork]:
        """Parse nmcli output into WiFiNetwork objects"""
        networks = []
        for line in output.strip().split('\n'):
            if not line:
                continue
            try:
                ssid, signal, security, in_use = line.split(':')
                networks.append(WiFiNetwork(
                    ssid=ssid,
                    signal_strength=int(signal),
                    security=security if security != '' else None,
                    in_use=(in_use == '*')
                ))
            except Exception as e:
                self.logger.error(f"Error parsing network: {line} - {e}")
        return networks

    async def _rescan_networks(self) -> None:
        """Force a rescan of available networks"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'rescan'
            ])
            if result.returncode != 0:
                self.logger.error(f"Network rescan failed: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error during network rescan: {e}")

    async def _scan_networks(self) -> List[WiFiNetwork]:
        """Scan for available networks"""
        try:
            result = self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
                'device', 'wifi', 'list'
            ])
            if result.returncode != 0:
                self.logger.error(f"Network scan failed: {result.stderr}")
                return []
            return self._parse_network_list(result.stdout)
        except Exception as e:
            self.logger.error(f"Error scanning networks: {e}")
            return []