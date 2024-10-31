from fastapi import APIRouter

from app.api.endpoints import file_manager, session_manager, s3_test_funcs

api_router = APIRouter()
api_router.include_router(file_manager.router, prefix='/main', tags=['main'])
api_router.include_router(session_manager.router, prefix='/upload', tags=['upload'])
api_router.include_router(s3_test_funcs.router, prefix='/test_s3', tags=['s3'])