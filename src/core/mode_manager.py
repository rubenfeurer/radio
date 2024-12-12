import asyncio
import logging
from enum import Enum
from typing import Optional
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
        self.logger = logger
        self._current_mode: NetworkMode = NetworkMode.UNKNOWN
        self._mode_lock = asyncio.Lock()
        self._switching = False
        
    @property
    def current_mode(self) -> NetworkMode:
        return self._current_mode
        
    @property
    def is_switching(self) -> bool:
        return self._switching

    async def detect_current_mode(self) -> NetworkMode:
        """Detect current network mode"""
        try:
            self.logger.debug("Detecting current network mode...")
            
            # Check if hostapd is running (AP mode)
            hostapd_result = await self._run_command([
                'systemctl', 'is-active', 'hostapd'
            ])
            self.logger.debug(f"Hostapd check result: {hostapd_result.stdout}")
            
            if hostapd_result.returncode == 0:
                self.logger.debug("Hostapd is running, setting AP mode")
                self._current_mode = NetworkMode.AP
                return self._current_mode

            # Check NetworkManager connection type
            nmcli_result = await self._run_command([
                'nmcli', '-t', '-f', 'TYPE,DEVICE', 'connection', 'show', '--active'
            ])
            self.logger.debug(f"NMCLI check result: {nmcli_result.stdout}")
            
            if 'wifi' in nmcli_result.stdout.lower() and 'wlan0' in nmcli_result.stdout:
                self.logger.debug("Active WiFi connection found on wlan0, setting CLIENT mode")
                self._current_mode = NetworkMode.CLIENT
            elif 'AP' in nmcli_result.stdout:
                self.logger.debug("AP connection found, setting AP mode")
                self._current_mode = NetworkMode.AP
            else:
                self.logger.debug("No definitive mode found, setting UNKNOWN")
                self._current_mode = NetworkMode.UNKNOWN
                
            return self._current_mode
            
        except Exception as e:
            self.logger.error(f"Error detecting mode: {e}")
            return NetworkMode.UNKNOWN

    async def switch_mode(self, target_mode: NetworkMode) -> bool:
        """Switch between AP and Client modes"""
        if self._switching:
            self.logger.warning("Mode switch already in progress")
            return False
            
        async with self._mode_lock:
            self._switching = True
            try:
                current = await self.detect_current_mode()
                if current == target_mode:
                    self.logger.info(f"Already in {target_mode.value} mode")
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
            self.logger.error(f"Error switching to AP mode: {e}")
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
            self.logger.error(f"Error switching to client mode: {e}")
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
            self.logger.error(f"Error during AP mode cleanup: {e}")

    async def _run_command(self, command: list) -> asyncio.subprocess.Process:
        """Run a shell command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Command failed: {stderr.decode()}")
            
        return type('CommandResult', (), {
            'stdout': stdout.decode(),
            'stderr': stderr.decode(),
            'returncode': process.returncode
        })

# Create singleton instance
mode_manager = ModeManager() 