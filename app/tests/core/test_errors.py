
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.core.exceptions import ERROR_CODES_MAP
from app.core.exceptions import EXC
from app.core.exceptions import ErrorCodes
from app.main import app

# Create a test client
client = TestClient(app)


# Example route to trigger exceptions
@app.get('/raise-http-exception/{error_code}')
async def raise_http_exception(error_code: int):
    if error_code <= len(ErrorCodes):
        raise EXC(ErrorCodes(error_code))

    raise HTTPException(status_code=404, detail='Not Found')


@app.get('/raise-validation-error')
async def raise_validation_error():
    raise RequestValidationError(errors=[{'loc': ['body'], 'msg': 'field required', 'type': 'value_error.missing'}])


def test_starlette_http_exception() -> None:
    index = len(ErrorCodes) + 1
    response = client.get(f'/raise-http-exception/{index}')  # This will raise a 404
    assert response.status_code == 500
    assert response.json() == {
        'msg': 'Not Found',
        'code': 5999,
        'details': {'code': None, 'custom': False, 'endpoint': f'/raise-http-exception/{index}'},
        'redirect': False,
        'notification': False,
    }


def test_http_exceptions() -> None:
    for i in range(1, len(ErrorCodes) + 1):
        response = client.get(f'/raise-http-exception/{i}')
        # 400 if inner code in 4000 and 500 if inner code in 5000
        assert response.status_code == response.json().get('code') // 1000 * 100

        assert response.json() == {
            'msg': ERROR_CODES_MAP.get(ErrorCodes(i)).get('msg'),
            'code': ERROR_CODES_MAP.get(ErrorCodes(i)).get('code'),
            'details': {'endpoint': f'/raise-http-exception/{i}'},
            'redirect': False,
            'notification': False,
        }


def test_validation_error():
    response = client.get('/raise-validation-error')
    print(response.json())
    assert response.status_code == 400
    assert response.json() == {
        'msg': ERROR_CODES_MAP.get(ErrorCodes.ValidationError).get('msg'),
        'code': ERROR_CODES_MAP.get(ErrorCodes.ValidationError).get('code'),
        'details': {
            'endpoint': '/raise-validation-error',
            'errors': {'loc': ['body'], 'msg': 'field required', 'type': 'value_error.missing'},
        },
        'redirect': False,
        'notification': False,
    }
