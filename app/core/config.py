import os
from typing import List

from pydantic import AnyHttpUrl, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=['../../.env', '../.env', '.env'],
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )

    API_V1_STR: str = '/api/v1'
    # SERVER_NAME: str
    # SERVER_HOST: AnyHttpUrl
    HOST: str =  os.getenv('HOST', '127.0.0.1')
    PORT: int = os.getenv('PORT', 8001)

    PROJECT_NAME: str = 'Default Project Name'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    # LOG_PATH: str = os.getenv('LOG_PATH', './logs')

    SESSION_EXPIRE_MINUTES: int = 60 * 24 * 365 # 1 year

    # S3
    S3_PUBLIC_DOMAIN: str = os.getenv('S3_DOMAIN', 'default-domain')
    S3_ENDPOINT: str = os.getenv('S3_ENDPOINT', 'default-endpoint')
    S3_ACCESS_KEY: str = os.getenv('S3_ACCESS_KEY')
    S3_SECRET_KEY: str = os.getenv('S3_SECRET_KEY')
    S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'default_bucket')
    S3_REGION_NAME: str = os.getenv('S3_REGION_NAME', 'eu-west-1')

    S3_SVAHA_WRITE_BUCKET: str = os.getenv('S3_SVAHA_WRITE_BUCKET')
    S3_SVAHA_WRITER_LOGIN: str = os.getenv('S3_SVAHA_WRITER_LOGIN')
    S3_SVAHA_WRITER_PASSWORD: str = os.getenv('S3_SVAHA_WRITER_PASSWORD')

    S3_SVAHA_READ_BUCKET: str = os.getenv('S3_SVAHA_READ_BUCKET')
    S3_SVAHA_READER_LOGIN: str = os.getenv('S3_SVAHA_READER_LOGIN')
    S3_SVAHA_READER_PASSWORD: str = os.getenv('S3_SVAHA_READER_PASSWORD')

    # RabbitMQ
    RABBITMQ_URL: str = os.getenv('RABBITMQ_URL', 'amqp://username:password@127.0.0.1/')
    RABBITMQ_HOST: str = os.getenv('RABBITMQ_HOST', '127.0.0.1')
    RABBITMQ_PORT: int = os.getenv('RABBITMQ_PORT', 5672)
    RABBITMQ_LOGIN: str = os.getenv('RABBITMQ_LOGIN', 'username')
    RABBITMQ_PASSWORD: str = os.getenv('RABBITMQ_PASSWORD', 'password')

    # Redis
    REDIS_HOST: str = os.getenv('REDIS_URL', '127.0.0.1')
    REDIS_PORT: int = os.getenv('REDIS_URL', 6379)
    REDIS_LOGIN: str = os.getenv('REDIS_LOGIN', 'username')
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', 'password')

    QUEUE_EXPIRE_SEC: int = 24 * 60 * 60

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default_factory=list)

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith('['):
            return [i.strip().rstrip('/') for i in v.split(',')]
        if isinstance(v, (list, str)):
            return v


try:
    settings = Settings()
except ValidationError as e:
    print(e)
