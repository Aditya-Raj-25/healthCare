from fastapi import APIRouter
from .endpoints import health
from app.voice.websocket import router as voice_router

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(voice_router, tags=["voice"])
