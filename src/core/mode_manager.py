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
            # Store scan results here
            self._scan_results = None
            
            # Temporarily switch to client mode
            success = await self.temp_switch_to_client_mode()
            if not success:
                logger.error("Failed to switch to client mode for scanning")
                return None

            # Wait for NetworkManager to initialize
            await asyncio.sleep(2)

            # Perform network scan using nmcli
            scan_result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY',
                'device', 'wifi', 'list'
            ])
            
            if scan_result.returncode == 0:
                self._scan_results = self._parse_scan_results(scan_result.stdout)

            # Switch back to AP mode
            await self.restore_previous_mode()
            
            return self._scan_results

        except Exception as e:
            logger.error(f"Error during network scan: {e}")
            await self.restore_previous_mode()
            return None

    async def temp_switch_to_client_mode(self) -> bool:
        """Temporarily switch to client mode"""
        if self._temp_mode_active:
            logger.warning("Already in temporary mode")
            return False

        async with self._mode_lock:
            try:
                self._temp_mode_active = True
                self._previous_mode = self._current_mode
                self._switching = True
                self._timeout_task = None

                # Switch to client mode
                success = await self._switch_to_client()
                if success:
                    self._current_mode = NetworkMode.CLIENT
                    
                    # Start timeout timer
                    self._timeout_task = asyncio.create_task(self._handle_temp_mode_timeout())
                    
                return success

            finally:
                self._switching = False

    async def restore_previous_mode(self) -> bool:
        """Restore the previous mode"""
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

                if self._previous_mode == NetworkMode.AP:
                    success = await self._switch_to_ap()
                elif self._previous_mode == NetworkMode.CLIENT:
                    success = await self._switch_to_client()

                if success:
                    self._current_mode = self._previous_mode
                    self._temp_mode_active = False
                    
                return success

            finally:
                self._switching = False

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
        print("Starting mode detection...")
        logger.debug("Starting mode detection...")
        
        try:
            # Check if hostapd is running (AP mode)
            print("Checking hostapd status...")
            logger.debug("Checking hostapd status...")
            hostapd_result = await self._run_command([
                'sudo', 'systemctl', 'is-active', 'hostapd'
            ])
            print(f"Hostapd result: {hostapd_result.stdout}, {hostapd_result.returncode}")
            logger.debug(f"Hostapd check result: stdout='{hostapd_result.stdout.strip()}', "
                         f"returncode={hostapd_result.returncode}")
            
            if hostapd_result.returncode == 0:
                print("Hostapd is running, setting AP mode")
                logger.debug("Hostapd is running, setting AP mode")
                self._current_mode = NetworkMode.AP
                return self._current_mode

            # Check NetworkManager connection type
            print("Checking NetworkManager connections...")
            nmcli_result = await self._run_command([
                'sudo', 'nmcli', '-t', '-f', 'TYPE,DEVICE', 'connection', 'show', '--active'
            ])
            print(f"NMCLI result: {nmcli_result.stdout}")
            logger.debug(f"NMCLI check result: '{nmcli_result.stdout.strip()}'")
            
            # Check for either 'wifi' or '802-11-wireless' with wlan0
            if '802-11-wireless:wlan0' in nmcli_result.stdout:
                print("Found wireless connection, setting CLIENT mode")
                logger.debug("Active WiFi connection found on wlan0, setting CLIENT mode")
                self._current_mode = NetworkMode.CLIENT
                return self._current_mode
            
            print(f"No wifi connection found in: {nmcli_result.stdout}")
            logger.debug(f"No wifi connection found in: '{nmcli_result.stdout}'")
            self._current_mode = NetworkMode.UNKNOWN
            return self._current_mode
            
        except Exception as e:
            print(f"Error in detect_current_mode: {str(e)}")
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
        """Switch to AP mode"""
        try:
            # 1. Stop NetworkManager WiFi
            await self._run_command(['sudo', 'systemctl', 'stop', 'NetworkManager'])
            
            # 2. Configure hostapd
            await self._configure_hostapd()
            
            # 3. Start hostapd
            await self._run_command(['sudo', 'systemctl', 'start', 'hostapd'])
            
            # 4. Configure dnsmasq
            await self._configure_dnsmasq()
            
            # 5. Start dnsmasq
            await self._run_command(['sudo', 'systemctl', 'start', 'dnsmasq'])
            
            # 6. Enable IP forwarding
            await self._run_command(['sudo', 'sysctl', 'net.ipv4.ip_forward=1'])
            
            # 7. Configure interface
            await self._configure_interface()
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching to AP mode: {e}")
            await self._cleanup_ap_mode()
            return False

    async def _switch_to_client(self) -> bool:
        """Switch to Client mode"""
        try:
            # 1. Stop AP services
            await self._run_command(['sudo', 'systemctl', 'stop', 'hostapd'])
            await self._run_command(['sudo', 'systemctl', 'stop', 'dnsmasq'])
            
            # 2. Disable IP forwarding
            await self._run_command(['sudo', 'sysctl', 'net.ipv4.ip_forward=0'])
            
            # 3. Reset interface
            await self._reset_interface()
            
            # 4. Start NetworkManager
            await self._run_command(['sudo', 'systemctl', 'start', 'NetworkManager'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching to client mode: {e}")
            return False

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

# Create singleton instance
mode_manager = ModeManager() 