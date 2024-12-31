from pydantic import BaseModel, Field
from typing import Optional, List


class VolumeRequest(BaseModel):
    volume: int


class AssignStationRequest(BaseModel):
    stationId: int
    name: str
    url: str
    country: Optional[str] = None
    location: Optional[str] = None


class WiFiConnectionRequest(BaseModel):
    ssid: str
    password: Optional[str] = None


class SystemInfo(BaseModel):
    hostname: str
    ip: str
    cpuUsage: str
    diskSpace: str
    temperature: str
    mode: str
    hotspot_ssid: Optional[str] = None
    internet_connected: bool = False


class ServiceStatus(BaseModel):
    name: str
    active: bool
    status: str


class WebAccess(BaseModel):
    api: bool
    ui: bool


class MonitorUpdate(BaseModel):
    type: str = "monitor_update"
    systemInfo: SystemInfo
    services: List[ServiceStatus]
    webAccess: WebAccess
    logs: List[str]


class NetworkAddRequest(BaseModel):
    ssid: str
    password: str
    priority: int = Field(default=1, ge=0, le=999)
