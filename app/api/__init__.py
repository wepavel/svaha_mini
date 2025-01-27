from fastapi import APIRouter

from app.api.endpoints import file_manager, s3_test_funcs, session_manager, test_webui, manual_levers, streaming

api_router = APIRouter()
api_router.include_router(file_manager.router, prefix='/files', tags=['files'])
api_router.include_router(session_manager.router, prefix='/session', tags=['session'])
api_router.include_router(streaming.router, prefix='/streaming', tags=['streaming'])
api_router.include_router(manual_levers.router, prefix='/manual-levers', tags=['manual-levers'])
api_router.include_router(test_webui.router, prefix='/test-webui', tags=['test-webui'])

# api_router.include_router(s3_test_funcs.router, prefix='/test_s3', tags=['s3'])
