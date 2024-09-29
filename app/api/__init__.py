from fastapi import APIRouter

from app.api.endpoints import main
from app.api.endpoints import upload

api_router = APIRouter(
    # responses={
    #     400: {"description": "Not found", 'code': 1232, 'msg': "Sas"},
    #     500: {"description": "Conflict in data"},
    # }
)
api_router.include_router(main.router, prefix='/main', tags=['main'])
api_router.include_router(upload.router, prefix='/upload', tags=['upload'])
