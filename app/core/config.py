import os

from pydantic import ValidationError
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=['../.env', '.env'],
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )
    API_V1_STR: str = ''
    # SERVER_NAME: str
    # SERVER_HOST: AnyHttpUrl
    HOST: str = '127.0.0.1'
    PORT: int = 8001

    PROJECT_NAME: str

    SESSION_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 seconds

    S3_ENDPOINT: str = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
    S3_ACCESS_KEY: str = os.getenv('S3_ACCESS_KEY', '7sjgV5RJTfSQHOc5vz3K')
    S3_SECRET_KEY: str = os.getenv('S3_SECRET_KEY', 'haqLbBYFdiHagtzg249YsDsMnPDgFyIrFHybSI7d')
    S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'svaha-mini')
    RABBITMQ_URL: str = os.getenv('RABBITMQ_URL', 'amqp://admin:administrator@127.0.0.1/')
    # REDIS_URL: str = os.getenv('REDIS_URL', 'redis://10.244.183.218:6379')

    REDIS_HOST: str = os.getenv('REDIS_URL', '127.0.0.1')
    REDIS_PORT: int = os.getenv('REDIS_URL', 6379)

    QUEUE_EXPIRE_SEC: int = 24 * 60 * 60
    # class Config:
    #     env_file = ['../.env', '.env']
    #     env_file_encoding = 'utf-8'
    #     case_sensitive = True


try:
    settings = Settings()
except ValidationError as e:
    print(e)
