from fastapi import APIRouter

from app.api.endpoints import events
from app.api.endpoints import files
from app.api.endpoints import info
from app.api.endpoints import manual_levers
from app.api.endpoints import s3_test_funcs
from app.api.endpoints import session
from app.api.endpoints import test_webui
from app.api.endpoints import utils

api_router = APIRouter()
api_router.include_router(session.router, prefix='/session', tags=['session'])
api_router.include_router(files.router, prefix='/files', tags=['files'])
api_router.include_router(events.router, prefix='/events', tags=['events'])
api_router.include_router(info.router, prefix='/info', tags=['info'])
api_router.include_router(manual_levers.router, prefix='/manual-levers', tags=['manual-levers'])
api_router.include_router(test_webui.router, prefix='/test-webui', tags=['test-webui'])
api_router.include_router(utils.router, prefix='/utils', tags=['utils'])

# api_router.include_router(s3_test_funcs.router, prefix='/test_s3', tags=['s3'])
