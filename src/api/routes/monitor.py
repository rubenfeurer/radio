import asyncio
import logging
import socket
import subprocess
from pathlib import Path

import psutil
from fastapi import APIRouter, WebSocket

from config.config import settings
from src.core.mode_manager import ModeManagerSingleton

from ..models.requests import SystemInfo

router = APIRouter(prefix="/monitor", tags=["Monitor"])

# Store active WebSocket connections
active_connections: set[WebSocket] = set()
broadcast_task = None

# Set logging level for monitor module
logging.getLogger("monitor").setLevel(logging.DEBUG)


async def get_system_info() -> SystemInfo:
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    cpu = psutil.cpu_percent()
    disk = psutil.disk_usage("/")

    # Get mode information
    mode_manager = ModeManagerSingleton.get_instance()
    current_mode = mode_manager.detect_current_mode()

    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = float(f.read()) / 1000.0
    except Exception:
        temp = 0

    # Check internet connectivity
    try:
        result = subprocess.run(
            ["nmcli", "networking", "connectivity", "check"],
            capture_output=True,
            text=True,
            check=False,
        )
        internet_connected = "full" in result.stdout.lower()
        logging.debug(f"[MONITOR] Internet connectivity check: {internet_connected}")
    except Exception as e:
        logging.exception(f"[MONITOR] Error checking internet connectivity: {e}")
        internet_connected = False

    # Get hotspot information
    try:
        result = subprocess.run(
            ["nmcli", "device", "show", "wlan0"],
            capture_output=True,
            text=True,
            check=False,
        )

        hotspot_ssid = None
        if "AP" in result.stdout or "Hotspot" in result.stdout:
            for line in result.stdout.splitlines():
                if "GENERAL.CONNECTION:" in line:
                    hotspot_ssid = line.split(":")[1].strip()
                    break
        logging.debug(f"[MONITOR] Current hotspot SSID: {hotspot_ssid}")
    except Exception as e:
        logging.exception(f"[MONITOR] Error getting hotspot info: {e}")
        hotspot_ssid = None

    system_info = SystemInfo(
        hostname=hostname,
        ip=ip,
        cpuUsage=f"{cpu}%",
        diskSpace=f"Used: {disk.percent}%",
        temperature=f"{temp:.1f}°C",
        mode=current_mode.value,
        hotspot_ssid=hotspot_ssid,
        internet_connected=internet_connected,
    )

    logging.debug(
        f"[MONITOR] System info update: mode={current_mode}, hotspot={hotspot_ssid}, internet={internet_connected}",
    )
    return system_info


async def get_services_status():
    # List of critical services
    services = [
        "NetworkManager",  # Network connectivity
        "avahi-daemon",  # mDNS/DNS-SD
        "pigpiod",  # GPIO daemon
        "dbus",  # System message bus
    ]
    result = []

    for service in services:
        cmd = ["systemctl", "is-active", service]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        status = stdout.decode().strip()
        active = status == "active"
        result.append({"name": service, "active": active, "status": status})

    return result


async def check_web_access():
    async def check_url(url):
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "--head",
                "--max-time",
                "2",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return b"200 OK" in stdout or b"304 Not Modified" in stdout
        except Exception:
            return False

    return {
        "api": await check_url(f"http://localhost:{settings.CONTAINER_PORT}/health"),
        "ui": await check_url(f"http://localhost:{settings.DEV_PORT}"),
    }


async def periodic_broadcast():
    """Periodically broadcast system updates to all connected clients"""
    logging.info("[MONITOR] Starting periodic broadcast task")
    counter = 0
    while True:
        try:
            if active_connections:
                counter += 1
                system_info = await get_system_info()
                # Convert Pydantic model to dict before accessing
                system_info_dict = system_info.dict()
                logging.debug(
                    f"[MONITOR] Broadcast #{counter}: CPU={system_info_dict['cpuUsage']}, Connections={len(active_connections)}",
                )

                status = {
                    "type": "monitor_update",
                    "data": {
                        "systemInfo": system_info_dict,  # Convert to dict
                        "services": await get_services_status(),
                    },
                }

                for connection in active_connections:
                    try:
                        await connection.send_json(status)
                    except Exception as e:
                        logging.exception(
                            f"[MONITOR] Error broadcasting to client: {e}",
                        )
                        active_connections.remove(connection)
            await asyncio.sleep(2)
        except Exception as e:
            logging.exception(f"[MONITOR] Error in periodic broadcast: {e}")
            await asyncio.sleep(2)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logging.info("[MONITOR] New WebSocket connection request")
    await websocket.accept()

    # Ensure clean state
    if websocket in active_connections:
        active_connections.remove(websocket)
    active_connections.add(websocket)

    logging.info(
        f"[MONITOR] WebSocket connection accepted. Total connections: {len(active_connections)}",
    )

    # Always restart broadcast task for new connections
    global broadcast_task
    if broadcast_task:
        broadcast_task.cancel()
    broadcast_task = asyncio.create_task(periodic_broadcast())

    try:
        while True:
            msg = await websocket.receive_text()
            logging.debug(f"Received WebSocket message: {msg}")
            if msg == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception as e:
        logging.exception(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logging.info(
            f"WebSocket disconnected. Remaining connections: {len(active_connections)}",
        )
        # Only cancel broadcast if truly no connections left
        if len(active_connections) == 0 and broadcast_task:
            broadcast_task.cancel()


# REST endpoint for initial data and fallback
@router.get("/status")
async def get_status():
    """Get current system status including services, system info, and web access"""
    return {
        "systemInfo": await get_system_info(),
        "services": await get_services_status(),
        "webAccess": await check_web_access(),
    }


async def get_recent_logs():
    log_file = Path("/home/radio/radio/logs/radio.log")
    if not log_file.exists():
        return []

    with open(log_file) as f:
        return f.readlines()[-10:]


@router.get("/system-info", response_model=SystemInfo)
async def get_system_info_endpoint() -> SystemInfo:
    mode_manager = ModeManagerSingleton.get_instance()
    mode = mode_manager.detect_current_mode()
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    return SystemInfo(
        mode=mode.value,
        hostname=hostname,
        ip=ip,
        cpuUsage=f"{psutil.cpu_percent()}%",
        diskSpace=f"Used: {psutil.disk_usage('/').percent}%",
        temperature="N/A",  # Or implement actual temperature reading
        internet_connected=True,  # Implement actual check if needed
        hotspot_ssid=None,  # Implement if needed
    )
