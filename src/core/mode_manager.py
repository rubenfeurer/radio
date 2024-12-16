import asyncio
import logging
from enum import Enum
from typing import Optional, List
from config.config import settings
from src.utils.logger import logger
import os
import tempfile

class NetworkMode(Enum):
    CLIENT = "client"
    AP = "ap"
    UNKNOWN = "unknown"

class ModeManager:
    def __init__(self):
        self._current_mode: NetworkMode = NetworkMode.UNKNOWN
        self._previous_mode: NetworkMode = NetworkMode.UNKNOWN
        self._mode_lock = asyncio.Lock()
        self._switching = False
        self._temp_mode_active = False
        self._temp_mode_timeout = 30  # seconds
        self._scan_results = None
        
    @property
    def current_mode(self) -> NetworkMode:
        return self._current_mode
        
    @property
    def is_switching(self) -> bool:
        return self._switching

    @property
    def is_temp_mode(self) -> bool:
        return self._temp_mode_active

    async def scan_from_ap_mode(self) -> Optional[List[dict]]:
        """Temporarily switch to client mode, scan for networks, and return to AP mode"""
        if self._current_mode != NetworkMode.AP:
            logger.error("Can only scan from AP mode")
            return None

        try:
            logger.debug("Starting AP mode scan sequence")
            self._scan_results = None
            
            logger.debug("Attempting temporary switch to client mode")
            success = await self.temp_switch_to_client_mode()
            if not success:
                logger.error("Failed to switch to client mode for scanning")
                return None

            logger.debug("Successfully switched to client mode, waiting for NetworkManager")
            await asyncio.sleep(2)

            logger.debug("Performing network scan")
            scan_result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY',
                'device', 'wifi', 'list'
            ])
            
            if scan_result.returncode == 0:
                self._scan_results = self._parse_scan_results(scan_result.stdout)
                logger.debug(f"Scan successful, found {len(self._scan_results)} networks")
            else:
                logger.error("Scan command failed")

            logger.debug("Attempting to restore AP mode")
            restore_success = await self.restore_previous_mode()
            if not restore_success:
                logger.error("Failed to restore AP mode")
            else:
                logger.debug("Successfully restored AP mode")
            
            return self._scan_results

        except Exception as e:
            logger.error(f"Error during network scan: {e}")
            logger.debug("Attempting to restore AP mode after error")
            await self.restore_previous_mode()
            return None

    async def temp_switch_to_client_mode(self) -> bool:
        """Temporarily switch to client mode"""
        logger.debug(f"Entering temp_switch_to_client_mode. Current state: temp_active={self._temp_mode_active}, current_mode={self._current_mode}")
        
        if self._temp_mode_active:
            logger.warning("Already in temporary mode")
            return False

        async with self._mode_lock:
            try:
                self._previous_mode = self._current_mode
                success = await self._switch_to_client()
                
                if success:
                    self._temp_mode_active = True
                    self._current_mode = NetworkMode.CLIENT
                    # Start timeout handler
                    self._timeout_task = asyncio.create_task(self._handle_temp_mode_timeout())
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Error switching to client mode: {e}")
                self._temp_mode_active = False
                return False

    async def restore_previous_mode(self) -> bool:
        """Restore the previous mode"""
        logger.debug(f"Entering restore_previous_mode. Current state: temp_active={self._temp_mode_active}, previous_mode={self._previous_mode}, current_mode={self._current_mode}")
        
        if not self._temp_mode_active:
            logger.warning("Not in temporary mode")
            return False

        async with self._mode_lock:
            try:
                self._switching = True
                success = False

                # Cancel timeout task if it exists
                if hasattr(self, '_timeout_task') and self._timeout_task:
                    self._timeout_task.cancel()
                    try:
                        await self._timeout_task
                    except asyncio.CancelledError:
                        pass
                    self._timeout_task = None

                logger.debug(f"Attempting to restore to previous mode: {self._previous_mode}")
                
                if self._previous_mode == NetworkMode.AP:
                    success = await self._switch_to_ap()
                elif self._previous_mode == NetworkMode.CLIENT:
                    success = await self._switch_to_client()

                if success:
                    self._current_mode = self._previous_mode
                    self._temp_mode_active = False
                    logger.debug(f"Successfully restored to {self._current_mode} mode")
                else:
                    logger.error("Failed to restore previous mode")
                    
                return success

            finally:
                self._switching = False
                logger.debug(f"Exiting restore_previous_mode. Success={success}, current_mode={self._current_mode}")

    async def _handle_temp_mode_timeout(self):
        """Handle timeout for temporary mode"""
        await asyncio.sleep(self._temp_mode_timeout)
        if self._temp_mode_active:
            logger.warning("Temporary mode timeout, restoring previous mode")
            await self.restore_previous_mode()

    def _parse_scan_results(self, scan_output: str) -> List[dict]:
        """Parse nmcli scan results"""
        networks = []
        for line in scan_output.strip().split('\n'):
            if line:
                try:
                    ssid, signal, security = line.split(':')
                    if ssid:  # Skip empty SSIDs
                        networks.append({
                            'ssid': ssid,
                            'signal_strength': int(signal),
                            'security': security if security else None
                        })
                except Exception as e:
                    logger.error(f"Error parsing network: {line} - {e}")
        return networks

    async def detect_current_mode(self) -> NetworkMode:
        """Detect current network mode"""
        # If we're in temporary mode, return the current mode without detection
        if self._temp_mode_active:
            logger.debug(f"In temporary mode, returning current mode: {self._current_mode}")
            return self._current_mode
        
        logger.debug("Starting mode detection...")
        
        try:
            # Check if hostapd is running (AP mode)
            logger.debug("Checking hostapd status...")
            hostapd_result = await self._run_command([
                'sudo', 'systemctl', 'is-active', 'hostapd'
            ])
            logger.debug(f"Hostapd check result: stdout='{hostapd_result.stdout.strip()}', "
                         f"returncode={hostapd_result.returncode}")
            
            if hostapd_result.returncode == 0:
                logger.debug("Hostapd is running, setting AP mode")
                self._current_mode = NetworkMode.AP
                return self._current_mode

            # Check NetworkManager connection type
            logger.debug("Checking NetworkManager connections...")
            nmcli_result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'TYPE,DEVICE', 'connection', 'show', '--active'
            ])
            logger.debug(f"NMCLI check result: '{nmcli_result.stdout.strip()}'")
            
            # Check for either 'wifi' or '802-11-wireless' with wlan0
            if '802-11-wireless:wlan0' in nmcli_result.stdout:
                logger.debug("Active WiFi connection found on wlan0, setting CLIENT mode")
                self._current_mode = NetworkMode.CLIENT
                return self._current_mode
            
            logger.debug(f"No wifi connection found in: '{nmcli_result.stdout}'")
            self._current_mode = NetworkMode.UNKNOWN
            return self._current_mode
            
        except Exception as e:
            logger.error(f"Error in detect_current_mode: {str(e)}")
            logger.exception("Full traceback:")
            return NetworkMode.UNKNOWN

    async def switch_mode(self, target_mode: NetworkMode) -> bool:
        """Switch between AP and Client modes"""
        if self._switching:
            logger.warning("Mode switch already in progress")
            return False
            
        async with self._mode_lock:
            self._switching = True
            try:
                current = await self.detect_current_mode()
                if current == target_mode:
                    logger.info(f"Already in {target_mode.value} mode")
                    return True
                    
                if target_mode == NetworkMode.AP:
                    success = await self._switch_to_ap()
                else:
                    success = await self._switch_to_client()
                    
                if success:
                    self._current_mode = target_mode
                return success
                
            finally:
                self._switching = False

    async def _switch_to_ap(self) -> bool:
        """Switch to Access Point mode"""
        try:
            self._switching = True
            logger.debug("Switching to AP mode...")
            
            # Stop client mode services in correct order
            logger.debug("Stopping client mode services...")
            await self._run_command(['sudo', 'systemctl', 'stop', 'NetworkManager'])
            await self._run_command(['sudo', 'systemctl', 'stop', 'wpa_supplicant'])
            await asyncio.sleep(1)
            
            # Configure and start AP services
            logger.debug("Starting AP mode services...")
            await self._run_command(['sudo', 'systemctl', 'start', 'hostapd'])
            await self._run_command(['sudo', 'systemctl', 'start', 'dnsmasq'])
            
            # Verify services
            if not await self._verify_services(NetworkMode.AP):
                logger.error("Failed to verify AP services")
                await self._cleanup_failed_transition(NetworkMode.AP)
                return False
            
            self._current_mode = NetworkMode.AP
            return True
            
        except Exception as e:
            logger.error(f"Error switching to AP mode: {e}")
            await self._cleanup_failed_transition(NetworkMode.AP)
            return False
        finally:
            self._switching = False

    async def _switch_to_client(self) -> bool:
        """Switch to Client mode"""
        try:
            self._switching = True
            logger.debug("Switching to Client mode...")
            
            # Stop AP services
            logger.debug("Stopping AP services...")
            await self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'])
            await self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'])
            await asyncio.sleep(1)
            
            # Start client services in correct order
            logger.debug("Starting client mode services...")
            await self._run_command(['sudo', 'systemctl', 'start', 'wpa_supplicant'])
            await asyncio.sleep(1)  # Give wpa_supplicant time to initialize
            await self._run_command(['sudo', 'systemctl', 'start', 'NetworkManager'])
            
            # Verify services
            if not await self._verify_services(NetworkMode.CLIENT):
                logger.error("Failed to verify client services")
                await self._cleanup_failed_transition(NetworkMode.CLIENT)
                return False
            
            self._current_mode = NetworkMode.CLIENT
            return True
            
        except Exception as e:
            logger.error(f"Error switching to client mode: {e}")
            await self._cleanup_failed_transition(NetworkMode.CLIENT)
            return False
        finally:
            self._switching = False

    async def _verify_services(self, mode: NetworkMode) -> bool:
        """Verify that required services are running for the given mode"""
        try:
            if mode == NetworkMode.AP:
                hostapd = await self._run_command(['sudo', 'systemctl', 'is-active', 'hostapd'])
                dnsmasq = await self._run_command(['sudo', 'systemctl', 'is-active', 'dnsmasq'])
                wpa = await self._run_command(['sudo', 'systemctl', 'is-active', 'wpa_supplicant'])
                
                logger.debug(f"AP mode services status - hostapd: {hostapd.stdout}, "
                            f"dnsmasq: {dnsmasq.stdout}, wpa_supplicant: {wpa.stdout}")
                            
                return (hostapd.returncode == 0 and 
                        dnsmasq.returncode == 0 and 
                        wpa.returncode != 0)  # wpa_supplicant should be stopped
            else:
                nm = await self._run_command(['sudo', 'systemctl', 'is-active', 'NetworkManager'])
                wpa = await self._run_command(['sudo', 'systemctl', 'is-active', 'wpa_supplicant'])
                
                logger.debug(f"Client mode services status - NetworkManager: {nm.stdout}, "
                            f"wpa_supplicant: {wpa.stdout}")
                            
                return nm.returncode == 0 and wpa.returncode == 0
            
        except Exception as e:
            logger.error(f"Error verifying services: {e}")
            return False

    async def _cleanup_failed_transition(self, target_mode: NetworkMode) -> None:
        """Clean up after a failed mode transition"""
        try:
            logger.debug(f"Cleaning up failed transition to {target_mode}")
            if target_mode == NetworkMode.AP:
                # Stop all services and restart in client mode
                await self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'])
                await self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'])
                await self._run_command(['sudo', 'systemctl', 'start', 'wpa_supplicant'])
                await self._run_command(['sudo', 'systemctl', 'start', 'NetworkManager'])
            else:
                # Stop all services and restart in AP mode
                await self._run_command(['sudo', 'systemctl', 'stop', 'NetworkManager'])
                await self._run_command(['sudo', 'systemctl', 'stop', 'wpa_supplicant'])
                await self._run_command(['sudo', 'systemctl', 'start', 'hostapd'])
                await self._run_command(['sudo', 'systemctl', 'start', 'dnsmasq'])
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def _configure_hostapd(self) -> None:
        """Configure hostapd"""
        config = f"""
interface={settings.AP_INTERFACE}
driver=nl80211
ssid={settings.AP_SSID}
hw_mode=g
channel={settings.AP_CHANNEL}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={settings.AP_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(config)
            temp_path = temp_file.name

        try:
            await self._run_command(['sudo', 'mv', temp_path, '/etc/hostapd/hostapd.conf'])
            await self._run_command(['sudo', 'chmod', '600', '/etc/hostapd/hostapd.conf'])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _configure_dnsmasq(self) -> None:
        """Configure dnsmasq"""
        config = f"""
interface={settings.AP_INTERFACE}
dhcp-range={settings.AP_DHCP_RANGE_START},{settings.AP_DHCP_RANGE_END},12h
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(config)
            temp_path = temp_file.name

        try:
            await self._run_command(['sudo', 'mv', temp_path, '/etc/dnsmasq.conf'])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _configure_interface(self) -> None:
        """Configure network interface"""
        await self._run_command([
            'sudo', 'ip', 'addr', 'flush', 'dev', settings.AP_INTERFACE
        ])
        await self._run_command([
            'sudo', 'ip', 'addr', 'add', 
            f"{settings.AP_IP_ADDRESS}/24", 
            'dev', settings.AP_INTERFACE
        ])
        await self._run_command(['sudo', 'ip', 'link', 'set', settings.AP_INTERFACE, 'up'])

    async def _reset_interface(self) -> None:
        """Reset network interface"""
        await self._run_command([
            'sudo', 'ip', 'addr', 'flush', 'dev', settings.AP_INTERFACE
        ])
        await self._run_command(['sudo', 'ip', 'link', 'set', settings.AP_INTERFACE, 'up'])

    async def _cleanup_ap_mode(self) -> None:
        """Cleanup AP mode"""
        try:
            await self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'])
            await self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'])
            await self._run_command(['sudo', 'systemctl', 'start', 'NetworkManager'])
            await self._reset_interface()
        except Exception as e:
            logger.error(f"Error during AP mode cleanup: {e}")

    async def _run_command(self, command: list) -> asyncio.subprocess.Process:
        """Run a shell command asynchronously"""
        try:
            logger.debug(f"Running command: {' '.join(command)}")
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            
            logger.debug(f"Command result: returncode={process.returncode}, "
                         f"stdout='{stdout_str}', stderr='{stderr_str}'")
            
            # For systemctl is-active, non-zero return code is expected for inactive services
            if 'systemctl is-active' in ' '.join(command):
                return type('CommandResult', (), {
                    'stdout': stdout_str,
                    'stderr': stderr_str,
                    'returncode': process.returncode
                })
            
            # For other commands, raise exception on non-zero return code
            if process.returncode != 0:
                raise Exception(f"Command failed: stdout='{stdout_str}', stderr='{stderr_str}'")
            
            return type('CommandResult', (), {
                'stdout': stdout_str,
                'stderr': stderr_str,
                'returncode': process.returncode
            })
            
        except Exception as e:
            logger.error(f"Error running command '{' '.join(command)}': {str(e)}")
            raise

    async def _verify_connection(self, ssid: str) -> bool:
        """Verify if connected to specified network"""
        try:
            for attempt in range(20):  # Increase timeout to 20 seconds
                status = await self._run_command([
                    'sudo', 'nmcli', 'connection', 'show', '--active'
                ])
                
                if ssid in status.stdout and 'wlan0' in status.stdout:
                    # Additional verification
                    device_status = await self._run_command([
                        'sudo', 'nmcli', 'device', 'status'
                    ])
                    if 'connected' in device_status.stdout:
                        logger.debug(f"Connection verified after {attempt} attempts")
                        return True
                        
                await asyncio.sleep(1)
                logger.debug(f"Waiting for connection verification... ({attempt}/20)")
                
            logger.error("Connection verification timed out")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying connection: {e}")
            return False

    async def _create_wifi_connection(self, ssid: str, password: str) -> bool:
        """Create and activate a WiFi connection"""
        try:
            # First ensure WiFi is enabled
            await self._run_command(['sudo', 'nmcli', 'radio', 'wifi', 'on'])
            await asyncio.sleep(2)  # Give more time for wifi to initialize
            
            # Force a rescan
            logger.debug("Forcing network rescan...")
            try:
                await self._run_command(['sudo', 'nmcli', 'device', 'wifi', 'rescan'])
                await asyncio.sleep(5)  # Give more time for scan
            except Exception as e:
                logger.warning(f"Rescan failed (this is often normal): {e}")
            
            # List available networks to verify SSID is visible
            networks = await self._run_command([
                'sudo', 'nmcli', '--terse', '--fields', 'SSID', 'device', 'wifi', 'list'
            ])
            
            if ssid not in networks.stdout:
                logger.error(f"Network {ssid} not found in scan results")
                return False
            
            # Try to connect directly
            logger.debug(f"Attempting to connect to {ssid}")
            connect_result = await self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'connect', ssid,
                'password', password
            ])
            
            if "successfully activated" in connect_result.stdout:
                logger.debug("Connection command succeeded")
                return True
            
            logger.error(f"Connection command failed: {connect_result.stdout}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating WiFi connection: {e}")
            return False

    async def connect_to_wifi(self, ssid: str, password: str) -> bool:
        """Connect to a WiFi network"""
        logger.debug(f"Received connection request for SSID: {ssid} with password: ****")
        
        # Get initial device status
        status = await self._run_command(['sudo', 'nmcli', 'device', 'status'])
        logger.debug(f"Device status before connection attempt: {status.stdout}")
        
        try:
            # Create and activate connection
            if await self._create_wifi_connection(ssid, password):
                # Verify connection
                if await self._verify_connection(ssid):
                    logger.debug(f"Successfully connected to {ssid}")
                    return True
                
            logger.debug("Connection verification failed")
            
            # Clean up failed connection
            try:
                logger.debug(f"Removing failed connection: {ssid}")
                await self._run_command([
                    'sudo', 'nmcli', 'connection', 'delete', ssid
                ])
            except Exception as e:
                logger.error(f"Failed to remove connection: {e}")
                
            return False
            
        except Exception as e:
            logger.error(f"Connection attempt failed: {e}")
            return False

# Create singleton instance
mode_manager = ModeManager() 