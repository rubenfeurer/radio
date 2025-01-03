import asyncio
import json
import logging
import subprocess
from enum import Enum
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, ClassVar, Dict, Optional

from config.config import settings
from src.core.sound_manager import SoundManager, SystemEvent

from .services.network_service import get_network_service

# Set up logger
logger = logging.getLogger(__name__)


class NetworkMode(Enum):
    AP = "AP"
    CLIENT = "CLIENT"


class ModeManagerSingleton:
    _instance: ClassVar[Optional["ModeManagerSingleton"]] = None

    def __init__(self):
        if ModeManagerSingleton._instance is not None:
            raise Exception("Use get_instance() instead")
        self.logger = logging.getLogger(__name__)
        self.AP_SSID = settings.HOSTNAME
        self.AP_PASS = settings.AP_PASSWORD
        self._MODE_FILE = Path("/tmp/radio/radio_mode.json")
        self._current_mode = None
        self._sound_manager = SoundManager()
        self._load_state()
        self.network_service = get_network_service()

    @classmethod
    def get_instance(cls) -> "ModeManagerSingleton":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _save_state(self, mode: NetworkMode) -> None:
        """Save current mode to state file"""
        try:
            self._MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._MODE_FILE.write_text(json.dumps({"mode": mode.value}))
            logger.debug(f"Saved mode state: {mode.value}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> Optional[NetworkMode]:
        """Load mode from state file"""
        try:
            if self._MODE_FILE.exists():
                data = json.loads(self._MODE_FILE.read_text())
                mode = NetworkMode(data["mode"])
                logger.debug(f"Loaded mode state: {mode.value}")
                return mode
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
        return None

    def detect_current_mode(self) -> NetworkMode:
        """Detect current network mode based on actual network configuration."""
        try:
            logger.debug("Starting mode detection...")

            # Check if running as AP/Hotspot
            result = subprocess.run(
                ["nmcli", "device", "show", "wlan0"],
                capture_output=True,
                text=True,
                check=False,
            )

            logger.debug(f"Network status from nmcli: {result.stdout}")

            if "AP" in result.stdout or "Hotspot" in result.stdout:
                logger.info("Detected AP/Hotspot mode from network status")
                return NetworkMode.AP

            logger.info("Detected client mode from network status")
            return NetworkMode.CLIENT

        except Exception as e:
            logger.error(f"Error detecting mode: {e!s}", exc_info=True)
            return NetworkMode.AP  # Default to AP mode

    def _verify_mode(self, mode: NetworkMode) -> bool:
        """Verify that saved mode matches actual mode"""
        try:
            if mode == NetworkMode.AP:
                result = subprocess.run(
                    [
                        "nmcli",
                        "-t",
                        "-f",
                        "MODE",
                        "device",
                        "wifi",
                        "list",
                        "ifname",
                        "wlan0",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return "AP" in result.stdout
            result = subprocess.run(
                ["nmcli", "-t", "-f", "GENERAL.STATE", "device", "show", "wlan0"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "AP" not in result.stdout
        except Exception as e:
            self.logger.error(f"Mode verification failed: {e}")
            return False

    async def enable_ap_mode(self) -> bool:
        """Enable AP mode using NetworkManager"""
        try:
            logger.info(f"Enabling AP mode with SSID: {self.AP_SSID}")

            # Save current WiFi status before switching
            await self._save_wifi_status()

            # Create AP connection if it doesn't exist
            result = subprocess.run(
                [
                    "sudo",
                    "nmcli",
                    "device",
                    "wifi",
                    "hotspot",
                    "ifname",
                    "wlan0",
                    "ssid",
                    self.AP_SSID,
                    "password",
                    self.AP_PASS,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"Failed to create AP: {result.stderr}")
                return False

            self._save_state(NetworkMode.AP)
            return True

        except Exception as e:
            logger.error(f"Error enabling AP mode: {e}", exc_info=True)
            return False

    async def enable_client_mode(self) -> bool:
        """Enable client mode and connect to saved networks."""
        try:
            logger.info("Enabling client mode...")

            # 1. Stop and delete AP/Hotspot
            subprocess.run(
                ["sudo", "nmcli", "connection", "down", "Hotspot"],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["sudo", "nmcli", "connection", "delete", "Hotspot"],
                capture_output=True,
                check=False,
            )

            # 2. Switch to managed mode and enable WiFi
            subprocess.run(
                ["sudo", "nmcli", "device", "set", "wlan0", "managed"],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["sudo", "nmcli", "radio", "wifi", "on"],
                capture_output=True,
                check=False,
            )

            # 3. Force reconnection
            await asyncio.sleep(1)
            subprocess.run(
                ["sudo", "nmcli", "device", "connect", "wlan0"],
                capture_output=True,
                check=False,
            )

            # 4. Let NetworkManager auto-connect and wait for result
            max_attempts = 15
            connected = False
            for attempt in range(max_attempts):
                logger.debug(
                    f"Checking connection status (attempt {attempt + 1}/{max_attempts})",
                )
                check = subprocess.run(
                    ["nmcli", "-t", "-f", "GENERAL.STATE", "device", "show", "wlan0"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if "connected" in check.stdout.lower():
                    logger.info("Network connection established")
                    connected = True
                    break
                await asyncio.sleep(1)

            # 5. Save state and notify
            self._save_state(NetworkMode.CLIENT)

            if connected:
                await self._sound_manager.notify(SystemEvent.WIFI_CONNECTED)
                return True
            await self._sound_manager.notify(SystemEvent.STARTUP_ERROR)
            logger.warning("No connection established")
            return False

        except Exception as e:
            logger.error(f"Error enabling client mode: {e}", exc_info=True)
            await self._sound_manager.notify(SystemEvent.STARTUP_ERROR)
            raise

    async def toggle_mode(self) -> NetworkMode:
        """Toggle between AP and Client modes with stability checks"""
        try:
            # Allow interface to stabilize
            await asyncio.sleep(1)

            current_mode = self.detect_current_mode()
            if current_mode == NetworkMode.CLIENT:
                success = await self.enable_ap_mode()
            else:
                success = await self.enable_client_mode()

            # Verify mode switch
            if not success:
                self.logger.error(f"Failed to switch from {current_mode}")
                return current_mode

            # Allow mode to stabilize
            await asyncio.sleep(2)

            return self.detect_current_mode()

        except Exception as e:
            self.logger.error(f"Mode toggle failed: {e}")
            return current_mode

    def _run_command(
        self,
        cmd: list[str],
        check: bool = False,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[int] = None,
    ) -> CompletedProcess[str]:
        """Run a shell command and return the result"""
        try:
            return subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
            )
        except subprocess.SubprocessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}\nError: {e}")
            raise

    async def scan_wifi_networks(self) -> list[Dict[str, Any]]:
        """Scan for available WiFi networks."""
        try:
            logger.info("Scanning for WiFi networks...")
            current_mode = self.detect_current_mode()

            # If in AP mode, temporarily switch to client mode for scanning
            temp_switch = False
            if current_mode == NetworkMode.AP:
                logger.info("Temporarily switching to client mode for scanning")
                temp_switch = True
                # Don't disconnect yet, just prepare interface
                subprocess.run(
                    ["sudo", "nmcli", "device", "set", "wlan0", "managed"],
                    capture_output=True,
                    check=False,
                )

            # Perform the scan
            subprocess.run(
                ["sudo", "nmcli", "device", "wifi", "rescan"],
                capture_output=True,
                check=False,
            )
            await asyncio.sleep(2)  # Wait for scan to complete

            result = subprocess.run(
                ["sudo", "nmcli", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                check=False,
            )

            # If we temporarily switched modes, restore AP mode
            if temp_switch:
                logger.info("Restoring AP mode after scan")
                subprocess.run(
                    ["sudo", "nmcli", "device", "set", "wlan0", "ap"],
                    capture_output=True,
                    check=False,
                )

            # Parse the scan results
            networks = self._parse_network_scan(result.stdout)
            return networks

        except Exception as e:
            logger.error(f"Error scanning networks: {e}")
            raise

    async def recover_network_state(self) -> bool:
        """Recover last known network state after power loss or failure"""
        try:
            last_mode = self._load_state()
            if not last_mode:
                self.logger.warning("No saved state found, defaulting to client mode")
                return await self.enable_client_mode()

            self.logger.info(f"Recovering last known state: {last_mode}")
            if last_mode == NetworkMode.AP:
                return await self.enable_ap_mode()
            return await self.enable_client_mode()

        except Exception as e:
            self.logger.error(f"Failed to recover network state: {e}")
            # Default to client mode on failure
            return await self.enable_client_mode()


# For backwards compatibility
SimpleModeManager = ModeManagerSingleton
