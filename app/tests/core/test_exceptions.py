from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.core.exceptions import EXC
from app.core.exceptions import ErrorCode
from app.main import app

# Create a test client
client = TestClient(app)


# Example route to trigger exceptions
@app.get('/raise-http-exception/{error_code}')
async def raise_http_exception(error_code: int) -> None:
    for code in ErrorCode:
        if code.value.code == error_code:
            raise EXC(code)
    raise HTTPException(status_code=404, detail='Not Found')


@app.get('/raise-validation-error')
async def raise_validation_error() -> None:
    raise RequestValidationError(errors=[{'loc': ['body'], 'msg': 'field required', 'type': 'value_error.missing'}])


def test_starlette_http_exception() -> None:
    response = client.get('/raise-http-exception/5999')  # This will raise a 404
    assert response.status_code == 500

    assert response.json() == {
        'msg': 'Not Found',
        'code': 5999,
        'details': {'endpoint': '/raise-http-exception/5999'},
        'redirect': False,
        'notification': False,
        # 'custom': False
    }


def test_http_exceptions() -> None:
    for code in ErrorCode:
        response = client.get(f'/raise-http-exception/{code.value.code}')
        assert response.status_code == 400 if 4000 <= code.value.code < 5000 else 500

        expected_response = code.value.model_copy(deep=True)
        expected_response.details['endpoint'] = f'/raise-http-exception/{code.value.code}'

        # Excluding "custom" from comparison
        response_json = response.json()
        expected_json = expected_response.model_dump(exclude={'custom'})

        assert response_json == expected_json


def test_validation_error() -> None:
    response = client.get('/raise-validation-error')
    assert response.status_code == 400

    expected_response = ErrorCode.ValidationError.value.model_copy(deep=True)
    expected_response.details = {
        'endpoint': '/raise-validation-error',
        'errors': [{'loc': ['body'], 'msg': 'field required', 'type': 'value_error.missing'}],
    }
    expected_json = expected_response.model_dump(exclude={'custom'})

    assert response.json() == expected_json


# # Example route to trigger exceptions
# @app.get('/raise-http-exception/{error_code}')
# async def raise_http_exception(error_code: int) -> None:
#     if error_code in {item.value for item in ErrorCode}:
#         raise EXC(ErrorCode(error_code))
#
#     raise HTTPException(status_code=404, detail='Not Found')
#
#
# @app.get('/raise-validation-error')
# async def raise_validation_error() -> None:
#     raise RequestValidationError(errors=[{'loc': ['body'], 'msg': 'field required', 'type': 'value_error.missing'}])
#
#
# def test_starlette_http_exception() -> None:
#     response = client.get(f'/raise-http-exception/{5999}')  # This will raise a 404
#     assert response.status_code == 500
#     assert response.json() == {
#         'msg': 'Not Found',
#         'code': 5999,
#         'details': {'code': None, 'custom': False, 'endpoint': f'/raise-http-exception/{5999}'},
#         'redirect': False,
#         'notification': False,
#     }
#
#
# def test_http_exceptions() -> None:
#     for code in ErrorCode:
#         print(f'CODE: {code}; VALUE: {code.value}')
#         response = client.get(f'/raise-http-exception/{code.value}')
#         # 400 if inner code in 4000 and 500 if inner code in 5000
#         assert response.status_code == response.json().get('code') // 1000 * 100
#
#         assert response.json() == {
#             'msg': ERROR_CODES_MAP.get(code).get('msg'),
#             'code': ERROR_CODES_MAP.get(code).get('code'),
#             'details': {'endpoint': f'/raise-http-exception/{code.value}'},
#             'redirect': False,
#             'notification': False,
#         }
#
#
# def test_validation_error() -> None:
#     response = client.get('/raise-validation-error')
#     print(response.json())
#     assert response.status_code == 400
#     assert response.json() == {
#         'msg': ERROR_CODES_MAP.get(ErrorCodes.ValidationError).get('msg'),
#         'code': ERROR_CODES_MAP.get(ErrorCodes.ValidationError).get('code'),
#         'details': {
#             'endpoint': '/raise-validation-error',
#             'errors': {'loc': ['body'], 'msg': 'field required', 'type': 'value_error.missing'},
#         },
#         'redirect': False,
#         'notification': False,
#     }
