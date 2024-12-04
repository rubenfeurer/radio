from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket

app = FastAPI(title="Internet Radio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stations.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(websocket.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "Internet Radio API is running"}