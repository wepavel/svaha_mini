import uuid
from typing import Any
from typing import List

from sqlalchemy.ext.declarative import declared_attr
from sqlmodel import Enum
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel
from sqlmodel import create_engine

NEW_UUID = lambda: str(uuid.uuid4())


class Base(SQLModel):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class UserStatus(Base, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True, unique=True)
    status: str | None = Field(Enum('guest', 'subscriber', 'vip'))

    users: List['User'] = Relationship(back_populates='userstatus')


class User(Base, table=True):
    id: str | None = Field(primary_key=True, index=True, unique=True, default=NEW_UUID)
    login: str | None = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    reg_date: str
    is_superuser: bool = Field(default=False)
    user_status_id: int | None = Field(default=1, foreign_key='userstatus.id')
    userstatus: UserStatus | None = Relationship(back_populates='users')


sqlite_file_name = 'database.db'
sqlite_url = f'sqlite:///{sqlite_file_name}'

connect_args = {'check_same_thread': False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
