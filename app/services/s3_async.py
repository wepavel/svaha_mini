from functools import wraps
from io import BytesIO
import logging
import os
from typing import Any, Dict, List
import zipfile

import aioboto3
from botocore import client as botocore_client
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger

logging.getLogger('aioboto3').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)


class S3Manager:
    def __init__(self, local: bool = True) -> None:
        self.local = local
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region_name = settings.S3_REGION_NAME
        self.s3_access_key_id = settings.S3_ACCESS_KEY
        self.s3_secret_access_key = settings.S3_SECRET_KEY

        self.session = aioboto3.Session()

    async def get_client(self) -> BaseClient:
        if self.local:
            # If use minio
            return self.session.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=self.s3_access_key_id,
                aws_secret_access_key=self.s3_secret_access_key,
                config=botocore_client.Config(signature_version='s3v4'),
                verify=False,
            )
        return self.session.client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=self.s3_access_key_id,
            aws_secret_access_key=self.s3_secret_access_key,
        )

    async def check_s3_connection(self) -> None:
        try:
            async with await self.get_client() as client:
                await client.head_bucket(Bucket=self.bucket_name)
                logger.info('Successfully connected to the S3 server.')
        except ClientError as e:
            logger.error('Failed to connect to the S3 server. Please check the connection settings.')
            raise e

    @staticmethod
    def handle_s3_exceptions(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result
            except ClientError as e:
                logger.error(f'{func.__name__} failed: {e}')
                # Return None if the function should return a value
                if func.__annotations__.get('return') is not None:
                    return None

        return wrapper

    @handle_s3_exceptions
    async def download_file(self, file_key: str, local_path: str) -> None:
        async with await self.get_client() as client:
            await client.download_file(self.bucket_name, file_key, local_path)

    # @handle_s3_exceptions
    # async def upload_file(self, file: str | bytes, file_key: str) -> None:
    #     async with self.s3_client as client:
    #         await client.upload_file(file, self.bucket_name, file_key)

    @handle_s3_exceptions
    async def upload_file(self, file: str | bytes, file_key: str) -> None:
        async with await self.get_client() as client:
            if isinstance(file, BytesIO):
                await client.upload_fileobj(file, self.bucket_name, file_key)
            elif isinstance(file, str):
                await client.upload_file(file, self.bucket_name, file_key)

    @handle_s3_exceptions
    async def delete_object(self, file_key: str) -> None:
        async with await self.get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=file_key)

    async def delete_dir(self, dir_key: str) -> None:
        async with await self.get_client() as client:
            response = await client.list_objects_v2(Bucket=self.bucket_name, Prefix=dir_key)
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                if not file_key.endswith('/'):
                    await self.delete_object(file_key)

    async def download_files_from_dir(self, *, dir_key: str, local_dir: str, overwrite: bool = False) -> None:
        """Download all files in a directory from S3 to a local directory

        :param dir_key: the key of the directory in S3, e.g. 'foo/bar/'
        Note: we assume that dir_key ends with a slash
        :param local_dir: the path of the local directory to save the files, e.g. '/tmp/foo/bar/'
        :param overwrite: overwrite file if exists or pass
        """
        with await self.get_client() as client:
            response = await client.list_objects_v2(Bucket=self.bucket_name, Prefix=dir_key)
        if 'Contents' in response:
            os.makedirs(local_dir, exist_ok=True)
            for obj in response['Contents']:
                file_key = obj['Key']
                if not file_key.endswith('/'):
                    file_name = os.path.basename(file_key)
                    local_path = os.path.join(local_dir, file_name)
                    if not os.path.exists(local_path) or overwrite:
                        await self.download_file(file_key, local_path)

    async def upload_files_to_dir(self, *, local_dir: str, dir_key: str) -> None:
        """Upload all files in a local directory to S3

        :param local_dir: the path of the local directory to upload the files, e.g. '/tmp/foo/bar/'
        :param dir_key: the key of the directory in S3, e.g. 'foo/bar/'
        Note: we assume that dir_key ends with a slash
        Create the directory in S3 if it does not exist
        """
        # Iterate over the files in the local directory and upload each file
        for file_name in os.listdir(local_dir):
            logger.debug(f'Uploading {file_name}')
            local_path = os.path.join(local_dir, file_name)

            file_key = os.path.join(dir_key, file_name)
            # Upload the file
            await self.upload_file(local_path, file_key)

    async def list_objects(self, dir_key: str) -> list:
        async with await self.get_client() as client:
            response = await client.list_objects_v2(Bucket=self.bucket_name, Prefix=dir_key)
        files_list = []
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                if not file_key.endswith('/'):
                    file_name = os.path.basename(file_key)
                    files_list.append(file_name)
        return files_list

    async def list_objects_with_date(self, dir_key: str) -> list:
        async with await self.get_client() as client:
            response = await client.list_objects_v2(Bucket=self.bucket_name, Prefix=dir_key)
        files_list = []
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                last_modified = obj['LastModified']
                if not file_key.endswith('/'):
                    file_name = os.path.basename(file_key)
                    files_list.append({'file_name': file_name, 'last_modified': last_modified})
        return files_list

    async def list_objects_full(self, dir_key: str = '') -> List[Dict[str, Any]]:
        async with await self.get_client() as client:
            response = await client.list_objects_v2(Bucket=self.bucket_name, Prefix=dir_key)
        return response.get('Contents', [])

    @handle_s3_exceptions
    async def get_file_info(self, file_key: str) -> Dict[str, Any] | None:
        async with await self.get_client() as client:
            response = await client.head_object(Bucket=self.bucket_name, Key=file_key)
        return response

    @staticmethod
    async def zip_directory(source_dir: str, destination_dir: str, archive_name: str | None = None) -> str:
        """
        Archives the contents of the source directory.
        Parameters:
        - source_dir (str): Path to the directory to be archived.
        - destination_dir (str): Path where the archive will be stored.
        - archive_name (str, optional): Name for the archive. If not provided, the name of the source directory is used.
        """
        if not archive_name:
            archive_name = os.path.basename(source_dir) + '.zip'
        destination_arch = os.path.join(destination_dir, archive_name)
        with zipfile.ZipFile(os.path.join(destination_dir, archive_name), 'w') as zf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file == archive_name:
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zf.write(file_path, arcname=arcname)
        logger.info(f'Archive {archive_name} created successfully in {destination_dir}')
        return destination_arch

    @staticmethod
    async def unzip_to_directory(archive_path: str, extract_to_dir: str, create_subdir: bool = True) -> None:
        """
        Unarchives the contents of the archive file.

        Parameters:
        - archive_path (str): Path to the archive file.
        - extract_to_dir (str): Directory where the contents will be extracted.
        - create_subdir (bool, optional): If True, create a subdirectory named after the archive file (without extension).
                                          If False, extract directly to the specified directory.
        """
        if create_subdir:
            base_name = os.path.splitext(os.path.basename(archive_path))[0]
            extract_to_dir = os.path.join(extract_to_dir, base_name)
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(extract_to_dir)
        logger.info(f'Archive {os.path.basename(archive_path)} extracted successfully to {extract_to_dir}')

    async def zip_directory_and_upload(
        self, source_dir: str, destination_dir: str | None = None, file_key: str | None = None
    ) -> str:
        if file_key is None:
            if destination_dir is None:
                msg = 'Zip and upload directory failed: destination_dir and file_key are empty.'
                logger.error(msg)
                raise ValueError(msg)
            file_key = os.path.join(destination_dir, os.path.basename(source_dir) + '.zip')
        if os.path.splitext(file_key)[-1].lower() != '.zip':
            msg = 'Zip and upload directory failed: file_key not valid .zip extension'
            logger.error(msg)
            raise ValueError(msg)
        target_arch = await self.zip_directory(source_dir, source_dir)
        await self.upload_file(local_path=target_arch, file_key=file_key)
        os.remove(target_arch)
        return file_key

    async def download_and_unzip(self, file_key: str, local_path: str, create_subdir: bool = True) -> None:
        base_name, base_ext = os.path.splitext(os.path.basename(file_key))
        if base_ext.lower() != '.zip':
            msg = 'Download and unzip failed: file_key not valid .zip extension'
            logger.error(msg)
            raise ValueError(msg)
        archive_path = os.path.join(local_path, base_name + '.zip')
        await self.download_file(file_key, archive_path)
        await self.unzip_to_directory(archive_path, local_path, create_subdir=create_subdir)


s3 = S3Manager()
