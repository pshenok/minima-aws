import os
import uuid
import logging
from typing import List
from dependencies import async_queue
from dependencies import rds_helper

from fastapi import (
    File,
    UploadFile,
    APIRouter,
    status,
    HTTPException,
    Query
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload")

ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "text/plain",  # .txt
    "text/markdown",  # .md
    "text/csv"  # .csv
]

@router.get(
    "/get_files/{user_id}",
    response_description='Retrieve files uploaded by user id',
)
async def get_files(user_id: str):
    """
    Retrieve the list of files uploaded by a user.

    Args:
        user_id (str): The user ID to retrieve files for.

    Returns:
        List: A list of files uploaded by the user.
    """
    if not user_id:
        logger.error("Empty user ID provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty user ID provided"
        )

    return rds_helper.fetch_records_by_user_id(user_id)

@router.get(
    "/get_files_status/{user_id}",
    response_description='Retrieve files statuses by user id',
)
async def get_files_status(user_id: str):
    """
    Retrieve the statuses of files uploaded by a user.

    Args:
        user_id (str): The user ID to retrieve file statuses for.

    Returns:
        List: A list of file statuses for the user.
    """
    if not user_id:
        logger.error("Empty user ID provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty user ID provided"
        )

    return rds_helper.fetch_file_statuses_by_user_id(user_id)

@router.post(
    "/upload_files/", 
    response_description='Upload files by user id',
)
async def upload_files(
    user_id: str, 
    files: List[UploadFile] = File(...)):
    """
    Handle the upload of multiple files, save them to a specified directory, 
    and enqueue their paths for further processing.

    Args:
        user_id (str): The user ID to associate with the uploaded files.
        files (List[UploadFile]): A list of files to be uploaded. Each file should be a PDF, DOC, or Excel.
    Returns:
        Response: A JSON response containing the UUIDs and filenames of successfully 
        uploaded files or an HTTP 400 error if any file is not an allowed type or is empty.
    """
    uploaded_files_info = []

    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            logger.error(f"Invalid file type: {file.content_type} for file {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.filename}. Allowed types: PDF, DOC, Excel.",
            )
            
        file_path = os.path.join("uploads", file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        async_message = {
            "user_id": user_id,
            "file_id": str(uuid.uuid4()),
            "file_path": file_path,
            "filename": file.filename
        }
        async_queue.enqueue(async_message)
        logger.info(f"File {file_path} uploaded successfully")
        uploaded_files_info.append(async_message)
    return { "files": uploaded_files_info }

@router.post(
    "/remove_file/", 
    response_description='remove file by file id and user id',
)
async def remove_file(file_ids: List[str], user_id: str):
    """
    Remove a file from the system.
    Args:
        file_ids (List[str]): The IDs of the files to remove.
        user_id (str): The ID of the user who uploaded the file.
    """

    if not file_ids:
        logger.error("Empty file IDs provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file ID provided"
        )

    if not user_id:
        logger.error("Empty user ID provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty user ID provided"
        )

    return rds_helper.delete_document(file_ids, user_id)