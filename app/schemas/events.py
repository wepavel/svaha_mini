from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class NotificationType(str, Enum):
    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'
    SUCCESS = 'SUCCESS'


class Position(str, Enum):
    LEFT_TOP = 'left-top'
    LEFT_BOTTOM = 'left-bottom'
    RIGHT_TOP = 'right-top'
    RIGHT_BOTTOM = 'right-bottom'
    CENTER = 'center'


class EventData(BaseModel):
    id: str
    message: str
    notification_type: NotificationType = Field(default=NotificationType.SUCCESS)
    position: Position = Field(default=Position.RIGHT_BOTTOM)
    info: dict | None = None


class Event(BaseModel):
    name: str
    data: EventData

    def as_sse_dict(self) -> dict[str, str]:
        return {
            'event': self.name,
            'data': self.data.model_dump(),
        }
