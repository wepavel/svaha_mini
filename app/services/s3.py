import boto3

from app.core.config import settings


class S3:
    def __init__(self) -> None:

        self.s3_client = boto3.resource(
            's3',
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            aws_session_token=None,
            config=boto3.session.Config(signature_version='s3v4'),
            verify=False,
        )

    def generate_presigned_url(self, file_name: str, file_type: str) -> str:
        return self.s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': file_name, 'ContentType': file_type},
            ExpiresIn=3600,
        )

    def upload_file(self, file_name: str, file_path: str) -> None:
        self.s3_client.Bucket(settings.S3_BUCKET_NAME).upload_file(file_path, file_name)


s3 = S3()
