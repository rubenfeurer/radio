import asyncio
from fastapi import APIRouter, WebSocket
import psutil
import subprocess
import socket
from pathlib import Path
from ..models.requests import SystemInfo, ServiceStatus, WebAccess, MonitorUpdate
from src.core.mode_manager import ModeManagerSingleton

router = APIRouter(
    prefix="/monitor",
    tags=["Monitor"]
)

async def get_system_info() -> SystemInfo:
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    cpu = psutil.cpu_percent()
    disk = psutil.disk_usage('/')
    
    # Get mode information
    mode_manager = ModeManagerSingleton.get_instance()
    current_mode = mode_manager.detect_current_mode()
    
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            temp = float(f.read()) / 1000.0
    except:
        temp = 0
    
    # Get hotspot information
    try:
        result = subprocess.run(['nmcli', 'device', 'show', 'wlan0'], 
                              capture_output=True, text=True)
        
        hotspot_ssid = None
        if 'AP' in result.stdout or 'Hotspot' in result.stdout:
            for line in result.stdout.splitlines():
                if 'GENERAL.CONNECTION:' in line:
                    hotspot_ssid = line.split(':')[1].strip()
                    break
    except Exception as e:
        logger.error(f"Error getting hotspot info: {e}")
        hotspot_ssid = None
    
    return SystemInfo(
        hostname=hostname,
        ip=ip,
        cpuUsage=f"{cpu}%",
        diskSpace=f"{disk.free // (2**30)} GB free",
        temperature=f"{temp:.1f}°C",
        hotspot_ssid=hotspot_ssid,
        mode=current_mode.value.lower()  # Add mode to system info
    )

async def get_services_status():
    # List of critical services
    services = [
        'NetworkManager',  # Network connectivity
        'avahi-daemon',    # mDNS/DNS-SD
        'pigpiod',         # GPIO daemon
        'dbus',           # System message bus
        'ssh'             # SSH access
    ]
    result = []
    
    for service in services:
        cmd = ['systemctl', 'is-active', service]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        status = stdout.decode().strip()
        active = status == 'active'
        result.append({
            "name": service,
            "active": active,
            "status": status
        })
    
    return result

async def check_web_access():
    async def check_url(url):
        try:
            proc = await asyncio.create_subprocess_exec(
                'curl', '-s', '--head', '--max-time', '2', url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return b'200 OK' in stdout or b'304 Not Modified' in stdout
        except:
            return False

    return {
        "api": await check_url('http://localhost:80/health'),
        "ui": await check_url('http://localhost:5173')
    }

# Add a REST endpoint for single status check
@router.get("/status", tags=["Monitor"])
async def get_status():
    """
    Get current system status including services, system info, and web access
    """
    return {
        "systemInfo": await get_system_info(),
        "services": await get_services_status(),
        "webAccess": await check_web_access()
    }

async def get_recent_logs():
    log_file = Path('/home/radio/radio/logs/radio.log')
    if not log_file.exists():
        return []
    
    with open(log_file) as f:
        return f.readlines()[-10:]