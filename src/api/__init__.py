from fastapi import FastAPI
from .routes import router

app = FastAPI(title="Radio API")
app.include_router(router)
