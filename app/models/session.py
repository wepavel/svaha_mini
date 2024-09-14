from pydantic import BaseModel


class SessionPublic(BaseModel):
    session_id: str
    position: int | None = None


class Session(SessionPublic):
    status: str
    download_url: str = None
    estimated_time: int | None = None
    completed_timestamp: float | None = None
    timestamp: float = None
