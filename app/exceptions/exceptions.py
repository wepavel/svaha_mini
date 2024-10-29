import json

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse


def exception_handler(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        try:
            errors = json.loads(exc.detail)
        except Exception:
            errors = exc.detail
        if type(errors) is not dict:
            errors = {'msg': errors, 'redirect': False}
        errors['endpoint'] = request.url.__dict__.get('_url', None)
        # return JSONResponse(status_code=400, content=jsonable_encoder({'detail': errors}))
        return JSONResponse(status_code=400, content=jsonable_encoder({'detail': errors}))
