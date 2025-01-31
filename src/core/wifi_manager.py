import subprocess
from subprocess import CompletedProcess
from typing import Optional

from src.utils.logger import setup_logger

from .models import WiFiNetwork, WiFiStatus
from .services.network_service import get_network_service

logger = setup_logger()


class WiFiManager:
    """Manages WiFi connections using NetworkManager"""

    def __init__(self, skip_verify: bool = False):
        """Initialize WiFi manager

        Args:
            skip_verify (bool): Skip NetworkManager verification in testing

        """
        self.logger = logger
        self.network_service = get_network_service()
        self._interface = "wlan0"
        self._skip_verify = skip_verify

    def _verify_networkmanager(self) -> None:
        """Verify NetworkManager is running"""
        if self._skip_verify:
            return

        try:
            result = self._run_command(["systemctl", "is-active", "NetworkManager"])
            if result.returncode != 0:
                raise RuntimeError("NetworkManager service is not active")
        except Exception as e:
            self.logger.error("NetworkManager verification failed: %s", str(e))
            raise RuntimeError("NetworkManager is not running") from e

    def get_current_status(self) -> WiFiStatus:
        """Get current WiFi status"""
        try:
            # Get list of saved connections with basic info first
            saved_result = self._run_command(
                [
                    "sudo",
                    "nmcli",
                    "-t",
                    "-f",
                    "NAME,TYPE,FILENAME",
                    "connection",
                    "show",
                ],
                capture_output=True,
                text=True,
            )

            self.logger.debug("\n=== Start Debug Output ===")
            self.logger.debug("1. Getting saved connections:")
            self.logger.debug(f"Command output: {saved_result.stdout}")

            # Track saved networks and their configuration files
            saved_networks = set()
            if saved_result.returncode == 0:
                for line in saved_result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    # Check for both 'wifi' and '802-11-wireless' in type field
                    if len(parts) >= 2 and (
                        "wifi" in parts[1].lower()
                        or "802-11-wireless" in parts[1].lower()
                    ):
                        conn_name = parts[0].strip()
                        saved_networks.add(conn_name)

                        # If it's a preconfigured connection, get the SSID from the config file
                        if conn_name == "preconfigured" and len(parts) >= 3:
                            try:
                                config_file = parts[2].strip()
                                config_result = self._run_command(
                                    ["sudo", "cat", config_file],
                                    capture_output=True,
                                    text=True,
                                )
                                if config_result.returncode == 0:
                                    for config_line in config_result.stdout.split("\n"):
                                        if "ssid=" in config_line.lower():
                                            ssid = config_line.split("=")[1].strip()
                                            saved_networks.add(ssid)
                                            self.logger.debug(
                                                f"Added preconfigured SSID: {ssid}",
                                            )
                            except Exception as e:
                                self.logger.error(
                                    f"Error reading preconfigured network: {e}",
                                )

                        self.logger.debug(f"Added saved connection: {conn_name}")

            self.logger.debug(f"\n2. Final saved_networks set: {saved_networks}")

            # Get current networks
            result = self._run_command(
                [
                    "sudo",
                    "nmcli",
                    "-t",
                    "-f",
                    "SSID,SIGNAL,SECURITY,IN-USE",
                    "device",
                    "wifi",
                    "list",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to get WiFi status: {result.stderr}")
                return WiFiStatus()

            self.logger.debug("\n3. Getting available networks:")
            self.logger.debug(f"Command output: {result.stdout}")

            networks = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    ssid, signal, security, in_use = line.split(":")
                    if ssid:  # Skip empty SSIDs
                        is_saved = (
                            ssid in saved_networks
                            or ssid.replace(" ", "") in saved_networks
                            or in_use
                            == "*"  # Always mark currently connected network as saved
                        )

                        self.logger.debug(f"\nProcessing network: {ssid}")
                        self.logger.debug(
                            f"  - In saved_networks: {ssid in saved_networks}",
                        )
                        self.logger.debug(
                            f"  - Without spaces: {ssid.replace(' ', '') in saved_networks}",
                        )
                        self.logger.debug(f"  - In use: {in_use == '*'}")
                        self.logger.debug(f"  - Final saved status: {is_saved}")

                        networks.append(
                            WiFiNetwork(
                                ssid=ssid,
                                signal_strength=int(signal),
                                security=security if security != "" else None,
                                in_use=(in_use == "*"),
                                saved=is_saved,
                            ),
                        )
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
                None,
            )

            # Check internet connectivity
            has_internet = False
            if current_network:
                internet_check = self._run_command(
                    ["sudo", "nmcli", "networking", "connectivity", "check"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                has_internet = (
                    internet_check.returncode == 0
                    and internet_check.stdout.strip() == "full"
                )

            # Create a mapping of SSIDs to connection names
            ssid_to_conn_name = {}
            if saved_result.returncode == 0:
                for line in saved_result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 2 and (
                        "wifi" in parts[1].lower()
                        or "802-11-wireless" in parts[1].lower()
                    ):
                        conn_name = parts[0].strip()
                        ssid_to_conn_name[conn_name] = conn_name
                        if conn_name == "preconfigured" and len(parts) >= 3:
                            try:
                                config_file = parts[2].strip()
                                config_result = self._run_command(
                                    ["sudo", "cat", config_file],
                                    capture_output=True,
                                    text=True,
                                )
                                if config_result.returncode == 0:
                                    for config_line in config_result.stdout.split("\n"):
                                        if "ssid=" in config_line.lower():
                                            ssid = config_line.split("=")[1].strip()
                                            ssid_to_conn_name[ssid] = conn_name
                                            self.logger.debug(
                                                f"Mapped SSID {ssid} to connection name {conn_name}",
                                            )
                            except Exception as e:
                                self.logger.error(
                                    f"Error reading preconfigured network: {e}",
                                )

            return WiFiStatus(
                ssid=current_network.ssid if current_network else None,
                signal_strength=(
                    current_network.signal_strength if current_network else None
                ),
                is_connected=bool(current_network),
                has_internet=has_internet,
                available_networks=aggregated_networks,
            )

        except Exception as e:
            self.logger.error(f"Error getting WiFi status: {e!s}", exc_info=True)
            return WiFiStatus()

    async def _scan_networks(self) -> list[WiFiNetwork]:
        """Scan for available networks"""
        try:
            result = self._run_command(
                [
                    "sudo",
                    "nmcli",
                    "-t",
                    "-f",
                    "SSID,SIGNAL,SECURITY,IN-USE",
                    "device",
                    "wifi",
                    "list",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
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
            output = self._run_command(["iwconfig", self._interface])
            if output and isinstance(output.stdout, str) and "ESSID:" in output.stdout:
                ssid = output.stdout.split('ESSID:"')[1].split('"')[0]
                if ssid:
                    quality = output.stdout.split("Quality=")[1].split(" ")[0]
                    level = (
                        int(quality.split("/")[0]) / int(quality.split("/")[1]) * 100
                    )
                    return WiFiNetwork(
                        ssid=ssid,
                        signal_strength=int(level),
                        security="WPA2",  # Assuming WPA2 as default
                        in_use=True,
                        saved=True,
                    )
            return None
        except Exception as e:
            self.logger.error(f"Error getting current connection: {e}")
            return None

    def _check_internet_connection(self) -> bool:
        """Check if there's internet connectivity"""
        try:
            # Try ping instead of nmcli connectivity check
            result = self._run_command(["ping", "-c", "1", "-W", "2", "8.8.8.8"])
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Internet check failed: {e}")
            return False

    def _run_command(self, command: list[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a shell command and return the result"""
        default_kwargs = {"capture_output": True, "text": True, "timeout": 5}
        kwargs = {**default_kwargs, **kwargs}
        try:
            return subprocess.run(command, **kwargs)
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="Command timed out",
            )
        except Exception as e:
            self.logger.error(f"Command failed: {' '.join(command)} - {e}")
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr=str(e),
            )

    async def connect_to_network(
        self,
        ssid: str,
        password: Optional[str] = None,
    ) -> bool:
        """Connect to a WiFi network"""
        try:
            self.logger.debug(
                f"Received connection request for SSID: {ssid} with password: {'(none)' if password is None else '****'}",
            )

            # Force a rescan to ensure network list is up to date
            await self._rescan_networks()

            # Check if network is saved
            saved_result = self._run_command(
                ["sudo", "nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                capture_output=True,
                text=True,
            )

            is_saved = False
            if saved_result.returncode == 0:
                for line in saved_result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[0].strip() == ssid:
                        is_saved = True
                        break

            # Verify network exists
            scan_result = self._run_command(
                [
                    "sudo",
                    "nmcli",
                    "-t",
                    "-f",
                    "SSID,SIGNAL,SECURITY,IN-USE",
                    "device",
                    "wifi",
                    "list",
                ],
                capture_output=True,
                text=True,
            )

            network_exists = False
            if scan_result.returncode == 0:
                for line in scan_result.stdout.strip().split("\n"):
                    if line.startswith(f"{ssid}:"):
                        network_exists = True
                        break

            if not network_exists:
                self.logger.error(f"Network {ssid} not found in scan results")
                return False

            # Connect to network
            if is_saved:
                self.logger.debug(f"Using saved connection for {ssid}")
                connect_result = self._run_command(
                    ["sudo", "nmcli", "connection", "up", ssid],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if connect_result.returncode != 0:
                    self.logger.error(f"Failed to connect: {connect_result.stderr}")
                    return False
            else:
                if not password:
                    self.logger.error("Password required for unsaved network")
                    return False

                self.logger.debug(f"Creating new connection for {ssid}")
                # Check the return value instead of ignoring it
                connect_result = self._run_command(
                    [
                        "sudo",
                        "nmcli",
                        "device",
                        "wifi",
                        "connect",
                        ssid,
                        "password",
                        password,
                    ],
                )
                if connect_result.returncode != 0:
                    self.logger.error(
                        f"Failed to create connection: {connect_result.stderr}",
                    )
                    return False

            # Verify connection was successful
            verify_result = self._run_command(
                [
                    "sudo",
                    "nmcli",
                    "-t",
                    "-f",
                    "GENERAL.STATE",
                    "device",
                    "show",
                    "wlan0",
                ],
                capture_output=True,
                text=True,
            )

            success = (
                verify_result.returncode == 0
                and "100 (connected)" in verify_result.stdout
            )
            self.logger.debug(f"Connection verification result: {success}")

            if not success and not is_saved:
                self._remove_connection(ssid)

            return success

        except Exception as e:
            self.logger.error(f"Error connecting to network: {e!s}", exc_info=True)
            return False

    def _remove_connection(self, ssid: str) -> bool:
        """Remove a saved connection"""
        try:
            self.logger.debug(f"Removing connection: {ssid}")
            result = self._run_command(
                ["sudo", "nmcli", "connection", "delete", ssid],
                capture_output=True,
                text=True,
            )
            success = result.returncode == 0
            if not success:
                self.logger.error(f"Failed to remove connection: {result.stderr}")
            return success
        except Exception as e:
            self.logger.error(f"Error removing connection: {e}")
            return False

    def _parse_network_list(
        self,
        output: str,
        saved_networks: Optional[set] = None,
    ) -> list[WiFiNetwork]:
        """Parse nmcli output into WiFiNetwork objects"""
        networks = []

        if saved_networks is None:
            # Get saved networks if not provided
            saved_result = self._run_command(
                ["sudo", "nmcli", "-t", "-f", "NAME", "connection", "show"],
                capture_output=True,
                text=True,
            )
            saved_networks = set()
            if saved_result.returncode == 0:
                saved_networks = set(saved_result.stdout.strip().split("\n"))

        for line in output.strip().split("\n"):
            if not line:
                continue
            try:
                ssid, signal, security, in_use = line.split(":")
                if ssid:  # Skip empty SSIDs
                    networks.append(
                        WiFiNetwork(
                            ssid=ssid,
                            signal_strength=int(signal),
                            security=security if security != "" else None,
                            in_use=(in_use == "*"),
                            saved=(ssid in saved_networks),
                        ),
                    )
            except Exception as e:
                self.logger.error(f"Error parsing network: {line} - {e}")
        return networks

    async def _rescan_networks(self) -> None:
        """Force a rescan of available networks"""
        try:
            result = self._run_command(
                ["sudo", "nmcli", "device", "wifi", "rescan"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                self.logger.error(f"Network rescan failed: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error during network rescan: {e}")

    def _aggregate_networks(self, networks: list[WiFiNetwork]) -> list[WiFiNetwork]:
        """Aggregate networks with the same SSID, keeping the strongest signal"""
        aggregated = {}
        for network in networks:
            if network.ssid not in aggregated:
                aggregated[network.ssid] = network
            else:
                # Update if signal is stronger or if current network is in use/saved
                existing = aggregated[network.ssid]
                if (
                    network.signal_strength > existing.signal_strength
                    or network.in_use
                    or network.saved
                ):
                    aggregated[network.ssid] = network

        return list(aggregated.values())

    def get_preconfigured_ssid(self) -> Optional[str]:
        """Get the SSID for the preconfigured connection"""
        try:
            config_file = (
                "/etc/NetworkManager/system-connections/preconfigured.nmconnection"
            )
            config_result = self._run_command(
                ["sudo", "cat", config_file],
                capture_output=True,
                text=True,
            )

            if config_result.returncode == 0:
                for line in config_result.stdout.split("\n"):
                    if "ssid=" in line.lower():
                        ssid = line.split("=")[1].strip()
                        self.logger.debug(f"Preconfigured SSID: {ssid}")
                        return ssid
        except Exception as e:
            self.logger.error(f"Error reading preconfigured network: {e}")
        return None

    def _create_new_connection(self, ssid: str, password: str) -> bool:
        try:
            if self._connection_exists(ssid):
                self.logger.debug(f"Connection already exists for {ssid}")
                return True

            self.logger.debug(f"Creating new connection for {ssid}")
            # Remove the result assignment completely
            self._run_command(
                [
                    "sudo",
                    "nmcli",
                    "device",
                    "wifi",
                    "connect",
                    ssid,
                    "password",
                    password,
                ],
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")
            return False

    def _connect_to_saved(self, ssid: str) -> bool:
        try:
            is_saved = self._connection_exists(ssid)
            if is_saved:
                self.logger.debug(f"Using saved connection for {ssid}")
                # Use the command result to determine success
                cmd_result = self._run_command(
                    ["sudo", "nmcli", "connection", "up", ssid],
                    capture_output=True,
                )
                return cmd_result.returncode == 0
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to saved network: {e}")
            return False

    def _check_process_output(
        self, process: CompletedProcess[str], expected: str
    ) -> bool:
        """Check if process output contains expected string"""
        if process and process.stdout:
            return expected in str(process.stdout)
        return False

    def _verify_interface_state(self) -> bool:
        """Verify wlan0 is in correct state"""
        try:
            result = self._run_command(
                ["nmcli", "device", "status"], capture_output=True, text=True
            )
            if "wlan0" not in result.stdout:
                self.logger.error("wlan0 interface not found")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Interface verification failed: {e}")
            return False
