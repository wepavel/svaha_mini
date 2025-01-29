from typing import Any

from fastapi import APIRouter
from fastapi import Request

from app.core.exceptions import ErrorResponse

router = APIRouter()


@router.get('/ping')
def get_ping_pong() -> str:
    return 'pong'


@router.post('/test-headers/')
def test_headers(request: Request) -> str:
    return f'headers {request.headers} cookies {request.cookies}'


@router.get('/test-error/{code}', description='code 1000 raise Exception, code 2000 raise ValueError, else Custom')
def test_error(code: int) -> Any:
    if code == 1000:
        msg = 'EXCEPTION'
        raise Exception(msg)
    if code == 2000:
        msg = 'ValueError'
        raise ValueError(msg)
    raise ErrorResponse(code=code)
