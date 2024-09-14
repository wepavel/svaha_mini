from fastapi import APIRouter

from app.api.endpoints import main

api_router = APIRouter()
api_router.include_router(main.router, prefix='/main', tags=['main'])
# api_router.include_router(status.router, prefix="/status", tags=["status"])
