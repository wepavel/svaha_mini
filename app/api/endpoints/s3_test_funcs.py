import time
from typing import Any

from fastapi import APIRouter, Cookie
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import EXC, ErrorCodes
from app.core.utils import generate_session_id
from app.models.session import Session, SessionPublic
from app.services.processing import send_to_queue
from app.services.redis_service import TaskStatus, redis_service

from app.services.s3_async import s3

router = APIRouter()


@router.get('/session')
async def get_session() -> None:
    """
    Test s3
    """

    # return response