import boto3
from botocore.client import Config

from app.core.config import settings

s3_client = boto3.client(
    's3',
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    config=Config(signature_version='s3v4'),
)


def generate_presigned_url(file_name: str, file_type: str) -> str:
    return s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': file_name, 'ContentType': file_type},
        ExpiresIn=3600,
    )
