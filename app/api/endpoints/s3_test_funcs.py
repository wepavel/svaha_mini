from io import BytesIO
from typing import Dict
from urllib.parse import quote

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from app.core.exceptions import EXC, ErrorCodes
from app.services.s3_async import s3

router = APIRouter()


@router.post('/upload/')
async def upload_file(key: str = '', file: UploadFile = File(...)) -> Dict[str, str]:
    try:
        contents = await file.read()
        file_stream = BytesIO(contents)
        file_stream.seek(0)
        await s3.upload_bytes_file(file_stream, key or file.filename)
        return {'message': 'File uploaded successfully'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.get('/download/{key:path}')
async def download_file(key: str) -> StreamingResponse:
    try:
        file_content = await s3.download_bytes_file(key)
        file_info = await s3.get_file_info(key)
        encoded_filename = quote(key.split('/')[-1])

        return StreamingResponse(
            content=file_content,
            media_type=file_info['ContentType'],
            headers={
                'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
                'Content-Type': file_info['ContentType'],
                'Content-Length': str(file_content.getbuffer().nbytes),
            },
        )

    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.get('/get_file_url/{key:path}')
async def get_file_url(key: str) -> RedirectResponse:
    try:
        presigned_url = await s3.get_file_url(key)

        return RedirectResponse(url=presigned_url, status_code=303)
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.delete('/delete/{key:path}')
async def delete_file(key: str) -> Dict[str, str]:
    try:
        await s3.delete_object(key)
        return {'message': 'File deleted successfully'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.delete('/delete_dir/{key:path}')
async def delete_dir(key: str) -> Dict[str, str]:
    try:
        await s3.delete_dir(key)
        return {'message': 'Directory deleted successfully'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.get('/list/')
async def list_files(prefix: str = '') -> JSONResponse:
    try:
        files = await s3.list_objects(prefix)
        return JSONResponse(content=files)
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.get('/list_with_date/')
async def list_files_with_date(prefix: str = '') -> JSONResponse:
    try:
        files = await s3.list_objects_with_date(prefix)
        return JSONResponse(content=files)
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.get('/info/')
async def get_file_info(key: str) -> JSONResponse:
    try:
        info = await s3.get_file_info(key)
        return JSONResponse(content=info)
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.post('/zip/')
async def zip_directory(source_dir: str = Form(...), destination_dir: str = Form(...), archive_name: str = None):
    try:
        archive_path = await s3.zip_directory(source_dir, destination_dir, archive_name)
        return {'message': f'Directory zipped successfully at {archive_path}'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.post('/unzip/')
async def unzip_directory(archive_path: str = Form(...), extract_to_dir: str = Form(...), create_subdir: bool = True):
    try:
        await s3.unzip_to_directory(archive_path, extract_to_dir, create_subdir)
        return {'message': f'Archive unzipped successfully to {extract_to_dir}'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.post('/zip_upload/')
async def zip_directory_and_upload(source_dir: str = Form(...), destination_dir: str = None, file_key: str = None):
    try:
        file_key = await s3.zip_directory_and_upload(source_dir, destination_dir, file_key)
        return {'message': f'Directory zipped and uploaded successfully as {file_key}'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})


@router.post('/download_unzip/')
async def download_and_unzip(file_key: str = Form(...), local_path: str = Form(...), create_subdir: bool = True):
    try:
        await s3.download_and_unzip(file_key, local_path, create_subdir)
        return {'message': f'File {file_key} downloaded and unzipped successfully to {local_path}'}
    except Exception as e:
        raise EXC(ErrorCodes.CoreFileUploadingError, details={'reason': str(e)})
