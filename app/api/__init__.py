from fastapi import APIRouter

from app.api.endpoints import file_manager as file_manager, session_manager as session_manager

api_router = APIRouter()
api_router.include_router(file_manager.router, prefix='/main', tags=['main'])
api_router.include_router(session_manager.router, prefix='/upload', tags=['upload'])
