import json

from fastapi import HTTPException


class EXC(HTTPException):
    def __init__(
        self, code: int, msg: str = None, redirect: bool = False, notification: bool = False, headers: dict = None
    ) -> None:
        message = {'status': code, 'msg': msg, 'redirect': redirect, 'notification': notification}
        if headers:
            message['headers'] = headers
        super().__init__(status_code=400, detail=json.dumps(message), headers=headers)
