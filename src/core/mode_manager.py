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
        self.logger = logger
        
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
            await asyncio.sleep(5)  # Increased delay for NetworkManager

            # Enable WiFi explicitly
            logger.debug("Enabling WiFi radio")
            await self._run_command(['sudo', 'nmcli', 'radio', 'wifi', 'on'])
            await asyncio.sleep(2)

            # Force a rescan first
            logger.debug("Forcing network rescan")
            rescan_result = await self._run_command([
                'sudo', 'nmcli', 'device', 'wifi', 'rescan'
            ])
            if rescan_result.returncode != 0:
                logger.error(f"Rescan failed: {rescan_result.stderr}")
            
            # Wait for rescan to complete
            await asyncio.sleep(3)

            # Now get the scan results
            logger.debug("Getting scan results")
            scan_result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY',
                'device', 'wifi', 'list'
            ])
            
            if scan_result.returncode == 0:
                self._scan_results = self._parse_scan_results(scan_result.stdout)
                logger.debug(f"Scan successful, found {len(self._scan_results)} networks")
                logger.debug(f"Networks found: {[n['ssid'] for n in self._scan_results]}")
            else:
                logger.error(f"Scan command failed: {scan_result.stderr}")

            return self._scan_results

        except Exception as e:
            logger.error(f"Error during network scan: {e}")
            return None
        finally:
            logger.debug("Attempting to restore AP mode")
            await self.restore_previous_mode()

    async def temp_switch_to_client_mode(self, timeout: int = None) -> bool:
        async with self._mode_lock:
            if self._temp_mode_active:
                return False
            
            try:
                self._previous_mode = self._current_mode
                if timeout:
                    self._temp_mode_timeout = timeout
                
                success = await self._switch_to_client()
                if success:
                    self._temp_mode_active = True
                    self._timeout_task = asyncio.create_task(
                        self._handle_temp_mode_timeout()
                    )
                return success
            except Exception as e:
                logger.error(f"Temp switch failed: {e}")
                await self._cleanup_failed_transition(NetworkMode.CLIENT)
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
                    success = await self.switch_to_ap_mode()
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
        async with self._mode_lock:
            if self._switching:
                logger.warning("Mode switch already in progress")
                return False
            self._switching = True
            try:
                current = await self.detect_current_mode()
                if current == target_mode:
                    logger.info(f"Already in {target_mode.value} mode")
                    return True
                    
                if target_mode == NetworkMode.AP:
                    success = await self.switch_to_ap_mode()
                else:
                    success = await self._switch_to_client()
                    
                if success:
                    self._current_mode = target_mode
                return success
                
            finally:
                self._switching = False

    async def switch_to_ap_mode(self):
        """Switch to Access Point mode"""
        try:
            self._switching = True
            logger.debug("Switching to AP mode...")
            
            # Stop client mode services in correct order
            logger.debug("Stopping client mode services...")
            await self._run_command(['sudo', 'systemctl', 'stop', 'NetworkManager'])
            await self._run_command(['sudo', 'systemctl', 'stop', 'wpa_supplicant'])
            await asyncio.sleep(1)
            
            # Configure interface
            logger.debug("Configuring AP interface...")
            await self._configure_interface()
            
            # Configure and start AP services
            logger.debug("Configuring hostapd and dnsmasq...")
            await self._configure_hostapd()
            await self._configure_dnsmasq()
            
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
        """Switch to client mode"""
        try:
            logger.debug("Switching to client mode...")
            
            # Stop AP services first and disable them
            logger.debug("Stopping and disabling AP mode services...")
            await self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'])
            await self._run_command(['sudo', 'systemctl', 'disable', 'hostapd'])
            await self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'])
            await self._run_command(['sudo', 'systemctl', 'disable', 'dnsmasq'])
            await asyncio.sleep(2)
            
            # Reset network interface
            logger.debug("Resetting network interface...")
            await self._run_command(['sudo', 'ip', 'link', 'set', settings.AP_INTERFACE, 'down'])
            await asyncio.sleep(1)
            await self._run_command(['sudo', 'ip', 'link', 'set', settings.AP_INTERFACE, 'up'])
            await asyncio.sleep(1)
            
            # Start and enable NetworkManager
            logger.debug("Starting and enabling NetworkManager...")
            await self._run_command(['sudo', 'systemctl', 'enable', 'NetworkManager'])
            await self._run_command(['sudo', 'systemctl', 'start', 'NetworkManager'])
            await asyncio.sleep(5)  # Increased wait time
            
            nm_status = await self._run_command(['sudo', 'systemctl', 'is-active', 'NetworkManager'])
            if nm_status.returncode != 0:
                logger.error("NetworkManager failed to start")
                return False
            
            # Start and enable wpa_supplicant
            logger.debug("Starting and enabling wpa_supplicant...")
            await self._run_command(['sudo', 'systemctl', 'enable', 'wpa_supplicant'])
            await self._run_command(['sudo', 'systemctl', 'start', 'wpa_supplicant'])
            await asyncio.sleep(3)
            
            # Enable WiFi explicitly
            logger.debug("Enabling WiFi radio...")
            await self._run_command(['sudo', 'nmcli', 'radio', 'wifi', 'on'])
            await asyncio.sleep(2)
            
            # Verify services are running
            if not await self._verify_services(NetworkMode.CLIENT):
                logger.error("Failed to verify client mode services")
                return False
            
            logger.debug("Successfully switched to client mode")
            return True
            
        except Exception as e:
            logger.error(f"Error switching to client mode: {e}")
            return False

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

    async def _cleanup_failed_transition(self, target_mode: NetworkMode) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self._stop_all_services()
                await self._reset_interface()
                await self._start_fallback_services(target_mode)
                
                if await self._verify_services(target_mode):
                    return True
                    
                logger.warning(f"Cleanup attempt {attempt + 1} failed")
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Cleanup attempt {attempt + 1} failed: {e}")
                
        return False

    async def _configure_hostapd(self) -> None:
        """Configure hostapd with the AP settings"""
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
country_code=CH
ieee80211n=1
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(config)
            temp_path = temp_file.name

        try:
            await self._run_command(['sudo', 'mv', temp_path, '/etc/hostapd/hostapd.conf'])
            await self._run_command(['sudo', 'chmod', '600', '/etc/hostapd/hostapd.conf'])
            # Enable the configuration
            await self._run_command(['sudo', 'systemctl', 'enable', 'hostapd'])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _configure_dnsmasq(self) -> None:
        """Configure dnsmasq"""
        config = f"""
interface={settings.AP_INTERFACE}
dhcp-range={settings.AP_DHCP_RANGE_START},{settings.AP_DHCP_RANGE_END},12h
address=/radiod.local/{settings.AP_IP_ADDRESS}
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
        """Verify if connected to specified network with extended checks"""
        try:
            for attempt in range(30):  # 30 second timeout
                # Check if NetworkManager is running
                nm_status = await self._run_command(['sudo', 'systemctl', 'is-active', 'NetworkManager'])
                if nm_status.returncode != 0:
                    logger.error("NetworkManager not running during verification")
                    return False
                    
                # Check active connection
                status = await self._run_command([
                    'sudo', 'nmcli', 'connection', 'show', '--active'
                ])
                
                if ssid in status.stdout and 'wlan0' in status.stdout:
                    # Additional verification
                    device_status = await self._run_command([
                        'sudo', 'nmcli', 'device', 'status'
                    ])
                    if 'connected' in device_status.stdout:
                        # Test internet connectivity
                        ping_result = await self._run_command([
                            'ping', '-c', '1', '-W', '2', '8.8.8.8'
                        ])
                        if ping_result.returncode == 0:
                            logger.debug(f"Connection verified after {attempt} attempts")
                            return True
                            
                await asyncio.sleep(1)
                logger.debug(f"Waiting for connection verification... ({attempt}/30)")
                
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

    async def connect_to_wifi(self, ssid: str, password: str = None) -> bool:
        """Connect to a WiFi network"""
        logger.debug(f"Received connection request for SSID: {ssid}")
        
        try:
            # Check if this is a preconfigured or saved network
            is_preconfigured = ssid == settings.PRECONFIGURED_SSID
            is_saved = await self._wifi_manager.is_network_saved(ssid)
            
            logger.debug(f"Network status - Preconfigured: {is_preconfigured}, Saved: {is_saved}")
            
            # For saved/preconfigured networks, switch directly to permanent client mode
            if is_preconfigured or is_saved:
                logger.debug("Using permanent client mode for saved/preconfigured network")
                if not await self._switch_to_client():
                    logger.error("Failed to switch to permanent client mode")
                    return False
                    
                # Create and activate connection
                if await self._create_wifi_connection(ssid, password):
                    if await self._verify_connection(ssid):
                        logger.debug(f"Successfully connected to saved network {ssid}")
                        return True
                        
                logger.error("Failed to connect to saved network")
                await self._switch_to_ap()
                return False
                
            else:
                # For new networks, use temporary mode initially
                logger.debug("Using temporary client mode for new network")
                if not await self.temp_switch_to_client_mode():
                    logger.error("Failed to switch to temporary client mode")
                    return False
                    
                # Try connecting
                if await self._create_wifi_connection(ssid, password):
                    if await self._verify_connection(ssid):
                        logger.debug("New network connected successfully, making permanent")
                        await self._wifi_manager.save_network(ssid)
                        self._temp_mode_active = False
                        self._current_mode = NetworkMode.CLIENT
                        self._previous_mode = NetworkMode.CLIENT
                        await self._enable_client_services()
                        return True
                        
                logger.debug("Connection verification failed")
                await self._switch_to_ap()
                return False
                
        except Exception as e:
            logger.error(f"Connection attempt failed: {e}")
            await self._switch_to_ap()
            return False

    async def _enable_client_services(self):
        """Enable client mode services for boot persistence"""
        await self._run_command(['sudo', 'systemctl', 'enable', 'NetworkManager'])
        await self._run_command(['sudo', 'systemctl', 'enable', 'wpa_supplicant'])
        await self._run_command(['sudo', 'systemctl', 'disable', 'hostapd'])
        await self._run_command(['sudo', 'systemctl', 'disable', 'dnsmasq'])

    async def force_client_mode(self) -> bool:
        """Force switch to client mode without temporary timeout"""
        async with self._mode_lock:
            try:
                self._switching = True
                success = await self._switch_to_client()
                if success:
                    self._current_mode = NetworkMode.CLIENT
                    self._temp_mode_active = False  # Ensure temp mode is off
                    await self._enable_client_services()
                return success
            finally:
                self._switching = False

# Create singleton instance
mode_manager = ModeManager() 