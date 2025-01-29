from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get('/track-settings')
async def get_track_settings() -> JSONResponse:
    settings = {
        'instrumental_settings': [
            {'id': 'bitcrusher', 'title': 'Bitcrusher', 'value': False, 'type': 'checkbox'},
        ],
        'voice_settings': [
            {
                'id': 'volume',
                'title': 'Volume',
                'type': 'slider',
                'value': 0,
                'min': -80,
                'max': 10,
                'step': 1,
                'startPoint': 0,
            },
            {
                'id': 'tonal_balance',
                'title': 'Tonal balance',
                'type': 'slider',
                'value': 50,
                'min': 0,
                'max': 100,
                'step': 1,
                'startPoint': 50,
            },
            {
                'id': 'hardness',
                'title': 'Hardness',
                'type': 'slider',
                'value': 7,
                'min': 0,
                'max': 10,
                'step': 1,
                'startPoint': 5,
            },
            {
                'id': 'echo',
                'title': 'Echo',
                'type': 'slider',
                'value': 10,
                'min': 0,
                'max': 10,
                'step': 1,
                'startPoint': 0,
            },
            {'id': 'autotune', 'title': 'Autotune', 'value': False, 'type': 'checkbox'},
        ],
        'style_settings': [
            {'id': 'foo', 'title': 'Foo', 'value': True, 'type': 'button'},
            {'id': 'bar', 'title': 'Bar', 'value': False, 'type': 'button'},
            {'id': 'baz', 'title': 'Baz', 'value': False, 'type': 'button'},
        ],
    }

    return JSONResponse(content=settings)
