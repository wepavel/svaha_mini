from app.core.config import Settings


def test_settings():
    # Testing successful creation of a Settings instance
    settings = Settings(
        API_V1_STR='/api/v1',
        PROJECT_NAME='test_project',
        HOST='localhost',
        PORT=8001,
        SESSION_EXPIRE_MINUTES=60 * 24 * 7,
        S3_ENDPOINT='http://localhost:9000',
        S3_ACCESS_KEY='test_access_key',
        S3_SECRET_KEY='test_secret_key',
        S3_BUCKET_NAME='test_bucket',
        RABBITMQ_URL='amqp://user:password@localhost/',
        RABBITMQ_LOGIN='user',
        RABBITMQ_PASSWORD='password',
        REDIS_HOST='localhost',
        REDIS_PORT=6379,
        REDIS_LOGIN='user',
        REDIS_PASSWORD='password',
        QUEUE_EXPIRE_SEC=24 * 60 * 60,
    )
    assert settings.API_V1_STR == '/api/v1'
    assert settings.PROJECT_NAME == 'test_project'
    assert settings.HOST == 'localhost'
    assert settings.PORT == 8001
    assert settings.SESSION_EXPIRE_MINUTES == 60 * 24 * 7
    assert settings.S3_ENDPOINT == 'http://localhost:9000'
    assert settings.S3_ACCESS_KEY == 'test_access_key'
    assert settings.S3_SECRET_KEY == 'test_secret_key'
    assert settings.S3_BUCKET_NAME == 'test_bucket'
    assert settings.RABBITMQ_URL == 'amqp://user:password@localhost/'
    assert settings.RABBITMQ_LOGIN == 'user'
    assert settings.RABBITMQ_PASSWORD == 'password'
    assert settings.REDIS_HOST == 'localhost'
    assert settings.REDIS_PORT == 6379
