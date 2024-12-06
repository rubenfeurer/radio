import asyncio
from typing import List, Optional
import subprocess
import logging
from .models import WiFiStatus, WiFiNetwork

logger = logging.getLogger(__name__)

class WiFiManager:
    """Manages WiFi connections using NetworkManager"""
    
    def __init__(self):
        self._interface = "wlan0"
        self._verify_networkmanager()
        
    def _verify_networkmanager(self) -> None:
        """Verify NetworkManager is installed and running"""
        try:
            result = self._run_command(["systemctl", "is-active", "NetworkManager"])
            if "active" not in result:
                raise RuntimeError("NetworkManager is not running")
        except Exception as e:
            logger.error(f"NetworkManager check failed: {e}")
            raise RuntimeError("NetworkManager is not running") from e

    def get_current_status(self) -> WiFiStatus:
        """Get current WiFi status including available networks"""
        try:
            logger.debug("Starting to get WiFi status...")
            
            # Get available networks
            logger.debug("Scanning for networks...")
            available_networks = self._scan_networks()
            logger.debug(f"Found {len(available_networks)} networks")
            
            # Get current connection details
            logger.debug("Getting current connection...")
            connection = self._get_current_connection()
            logger.debug(f"Current connection: {connection}")
            
            if connection:
                status = WiFiStatus(
                    ssid=connection.ssid,
                    signal_strength=connection.signal_strength,
                    is_connected=True,
                    has_internet=self._check_internet_connection(),
                    available_networks=available_networks
                )
                logger.debug(f"Returning connected status: {status}")
                return status
            
            # Return disconnected status with available networks
            status = WiFiStatus(available_networks=available_networks)
            logger.debug(f"Returning disconnected status: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Error getting WiFi status: {str(e)}", exc_info=True)
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

    def _run_command(self, command: list) -> str:
        """Run system command with sudo if needed"""
        try:
            # Add sudo for nmcli commands
            if command[0] == "nmcli":
                command = ["sudo"] + command
            
            logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
                raise RuntimeError(f"Command failed: {result.stderr}")
            
            logger.debug(f"Command output: {result.stdout.strip()}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            raise
        except Exception as e:
            logger.error(f"Error running command {command}: {str(e)}", exc_info=True)
            raise

    async def connect_to_network(self, ssid: str, password: str) -> bool:
        """Connect to a WiFi network using NetworkManager"""
        try:
            # Check if network exists in scan results
            networks = self._scan_networks()
            if not any(net.ssid == ssid for net in networks):
                logger.error(f"Network {ssid} not found in scan results")
                return False

            # Attempt to connect
            command = [
                "nmcli", "device", "wifi",
                "connect", ssid,
                "password", password,
                "ifname", self._interface
            ]
            
            self._run_command(command)
            
            # Verify connection was successful
            current = self._get_current_connection()
            return current is not None and current.ssid == ssid
            
        except Exception as e:
            logger.error(f"Error connecting to network {ssid}: {e}")
            return False