from fastapi import APIRouter
from config.config import settings
from .wifi import router as wifi_router
from .stations import router as stations_router
from .system import router as system_router
from .websocket import router as websocket_router
from .mode import router as mode_router
from .ap import router as ap_router

# Create combined router
api_router = APIRouter()

# Include all routers with their prefixes
api_router.include_router(stations_router, prefix=settings.API_V1_STR, tags=["stations"])
api_router.include_router(system_router, prefix=settings.API_V1_STR, tags=["system"])
api_router.include_router(wifi_router, prefix=settings.API_V1_STR, tags=["wifi"])
api_router.include_router(websocket_router, tags=["websocket"])
api_router.include_router(mode_router, prefix=settings.API_V1_STR, tags=["mode"])
api_router.include_router(ap_router, prefix=settings.API_V1_STR, tags=["ap"])

# Export the combined router
router = api_router 