from typing import List, Optional, Tuple
import logging
import asyncio
from .wifi_manager import WiFiManager
from .mode_manager import ModeManagerSingleton, NetworkMode
from .models import WiFiNetwork, WiFiStatus
from pathlib import Path
import json
from datetime import datetime

class ConnectionError(Exception):
    """Custom exception for connection errors"""
    def __init__(self, message: str, error_type: str):
        self.message = message
        self.error_type = error_type
        super().__init__(message)

class APManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.wifi_manager = WiFiManager()
        self.mode_manager = ModeManagerSingleton.get_instance()
        self.interface_stabilize_delay = 2  # seconds
        self.required_services = ['dnsmasq', 'avahi-daemon']

    async def verify_ap_mode(self) -> bool:
        """Verify that we're in AP mode"""
        try:
            current_mode = self.mode_manager.detect_current_mode()
            return current_mode == NetworkMode.AP
        except Exception as e:
            self.logger.error(f"Error verifying AP mode: {e}")
            return False

    async def scan_networks(self) -> List[WiFiNetwork]:
        """Scan for networks with proper service handling"""
        try:
            if not await self.verify_ap_mode():
                raise ConnectionError("Must be in AP mode to scan", "mode_error")

            # Store current AP configuration
            self.logger.info("Storing AP configuration before scan...")
            
            # Temporarily switch to client mode
            self.logger.info("Temporarily switching to client mode for scanning...")
            if not await self._handle_mode_switch(to_client_mode=True):
                raise ConnectionError("Failed to switch to client mode for scanning", "mode_error")

            await asyncio.sleep(2)  # Give interface time to stabilize

            try:
                # Perform the scan
                networks = await self.wifi_manager.get_available_networks()
                
                # Brief delay before switching back
                await asyncio.sleep(1)
                
                return networks
            finally:
                # Restore AP mode with delay
                self.logger.info("Restoring AP mode after scan...")
                await asyncio.sleep(1)  # Wait before switching back
                if not await self._handle_mode_switch(to_client_mode=False):
                    self.logger.error("Failed to restore AP mode after scan!")
                await asyncio.sleep(2)  # Give AP time to stabilize

        except Exception as e:
            self.logger.error(f"Error during network scan: {e}")
            # Ensure we're back in AP mode
            await asyncio.sleep(1)
            await self.mode_manager.enable_ap_mode()
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(str(e), "scan_error")

    async def get_ap_status(self) -> dict:
        """Get current AP mode status"""
        try:
            is_ap_mode = await self.verify_ap_mode()
            return {
                "is_ap_mode": is_ap_mode,
                "ap_ssid": self.mode_manager.AP_SSID if is_ap_mode else None,
                "available_networks": await self.scan_networks() if is_ap_mode else [],
                "saved_networks": await self.wifi_manager.get_saved_networks() if is_ap_mode else [],
                "preconfigured_ssid": self.wifi_manager.get_preconfigured_ssid()
            }
        except Exception as e:
            self.logger.error(f"Error getting AP status: {e}")
            raise 

    async def _ensure_mdns_service(self) -> None:
        """Ensure mDNS service is running after mode switch"""
        try:
            # Restart avahi-daemon to ensure mDNS works in new mode
            result = self.wifi_manager._run_command([
                'sudo', 'systemctl', 'restart', 'avahi-daemon'
            ], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Failed to restart avahi-daemon: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error ensuring mDNS service: {e}")

    async def _manage_ap_services(self, enable: bool) -> None:
        """Manage AP-related services when switching modes"""
        try:
            action = 'start' if enable else 'stop'
            for service in self.required_services:
                result = self.wifi_manager._run_command([
                    'sudo', 'systemctl', action, service
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Failed to {action} {service}: {result.stderr}")
                await asyncio.sleep(0.5)  # Brief delay between service operations
        except Exception as e:
            self.logger.error(f"Error managing AP services: {e}")

    async def _handle_mode_switch(self, to_client_mode: bool) -> bool:
        """
        Handle mode switching with proper service management
        Returns success status
        """
        try:
            # Stop AP services if switching to client mode
            if to_client_mode:
                await self._manage_ap_services(enable=False)
                success = await self.mode_manager.enable_client_mode()
            else:
                success = await self.mode_manager.enable_ap_mode()
                if success:
                    await self._manage_ap_services(enable=True)

            if success:
                await asyncio.sleep(self.interface_stabilize_delay)
                await self._ensure_mdns_service()
                # Verify network interface is up
                result = self.wifi_manager._run_command([
                    'sudo', 'ip', 'link', 'set', 'wlan0', 'up'
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Failed to bring up wlan0: {result.stderr}")

            return success

        except Exception as e:
            self.logger.error(f"Error during mode switch: {e}")
            return False

    async def get_saved_networks(self) -> Optional[WiFiStatus]:
        """Get the last saved WiFi status before switching to AP mode"""
        try:
            status_file = Path("data/last_wifi_status.json")
            if not status_file.exists():
                self.logger.warning("No saved WiFi status file found")
                return None

            with open(status_file) as f:
                data = json.load(f)

            # Convert the saved JSON data back to WiFiStatus model
            return WiFiStatus(
                ssid=data.get("ssid"),
                signal_strength=data.get("signal_strength"),
                is_connected=data.get("is_connected", False),
                has_internet=data.get("has_internet", False),
                available_networks=[
                    WiFiNetwork(
                        ssid=net["ssid"],
                        signal_strength=net["signal_strength"],
                        security=net.get("security"),
                        in_use=net.get("in_use", False),
                        saved=net.get("saved", False)
                    ) for net in data.get("available_networks", [])
                ]
            )

        except Exception as e:
            self.logger.error(f"Error reading saved WiFi status: {e}")
            return None

    async def add_network_connection(self, ssid: str, password: str, priority: int = 1) -> dict:
        """Add a new network connection with specified priority"""
        try:
            if not await self.verify_ap_mode():
                raise ConnectionError("Must be in AP mode to add connection", "mode_error")

            # Check if connection already exists and remove it
            result = self.wifi_manager._run_command([
                'sudo', 'nmcli', 'connection', 'show'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and ssid in result.stdout:
                self.logger.info(f"Removing existing connection for {ssid}")
                self.wifi_manager._run_command([
                    'sudo', 'nmcli', 'connection', 'delete', ssid
                ], capture_output=True, text=True)

            # Add the new connection
            result = self.wifi_manager._run_command([
                'sudo', 'nmcli', 'connection', 'add',
                'type', 'wifi',
                'con-name', ssid,
                'ifname', 'wlan0',
                'ssid', ssid,
                'wifi-sec.key-mgmt', 'wpa-psk',
                'wifi-sec.psk', password,
                'autoconnect', 'yes'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Failed to add connection: {result.stderr}")
                raise ConnectionError(
                    f"Failed to add connection: {result.stderr}",
                    "connection_error"
                )

            # Set the connection priority
            priority_result = self.wifi_manager._run_command([
                'sudo', 'nmcli', 'connection', 'modify',
                ssid,
                'connection.autoconnect-priority', str(priority)
            ], capture_output=True, text=True)

            if priority_result.returncode != 0:
                self.logger.warning(f"Failed to set priority: {priority_result.stderr}")

            return {
                "status": "success",
                "message": f"Successfully added connection for {ssid} with priority {priority}",
                "ssid": ssid,
                "priority": priority
            }

        except ConnectionError as e:
            raise
        except Exception as e:
            self.logger.error(f"Error adding network connection: {e}")
            raise ConnectionError(str(e), "unknown_error")

    async def modify_network_connection(self, ssid: str, password: str, priority: int = 1) -> dict:
        """Modify an existing network connection with new password and priority"""
        try:
            if not await self.verify_ap_mode():
                raise ConnectionError("Must be in AP mode to modify connection", "mode_error")

            # Check if connection exists
            result = self.wifi_manager._run_command([
                'sudo', 'nmcli', 'connection', 'show'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and ssid not in result.stdout:
                self.logger.error(f"Connection {ssid} does not exist")
                raise ConnectionError(
                    f"Connection {ssid} does not exist",
                    "not_found_error"
                )

            # Modify the existing connection
            modify_result = self.wifi_manager._run_command([
                'sudo', 'nmcli', 'connection', 'modify',
                ssid,
                'wifi-sec.psk', password,
                'connection.autoconnect', 'yes',
                'connection.autoconnect-priority', str(priority)
            ], capture_output=True, text=True)

            if modify_result.returncode != 0:
                self.logger.error(f"Failed to modify connection: {modify_result.stderr}")
                raise ConnectionError(
                    f"Failed to modify connection: {modify_result.stderr}",
                    "connection_error"
                )

            return {
                "status": "success",
                "message": f"Successfully modified connection for {ssid} with priority {priority}",
                "ssid": ssid,
                "priority": priority
            }

        except ConnectionError as e:
            raise
        except Exception as e:
            self.logger.error(f"Error modifying network connection: {e}")
            raise ConnectionError(str(e), "unknown_error")