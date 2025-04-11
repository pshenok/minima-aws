"""AWS S3 Helper class."""

import os
import re
import boto3
import json
import logging
import datetime
from typing import(
    List, 
    Union, 
    Callable, 
    Any, 
    Tuple
)

logger = logging.getLogger(__name__)

def serialize_datetime(obj):
    """Serialization helper"""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError('Type not serializable')


class AwsS3Helper:
    """
    Helper class for interacting with AWS S3.

    This class provides methods for various S3 operations, including uploading, downloading,
    listing, deleting files, and reading and writing JSON files.

    Note: All methods in this class are static, and you can use them without creating an instance of the class.
    """

    @staticmethod
    def get_client(name: str) -> boto3.client:
        """
        Get a boto3 client for the specified service.

        Args:
            name (str): The name of the AWS service.

        Returns:
            boto3.client: Boto3 client for the specified service.
        """
        # Check if we have an environment endpoint with the client name
        endpoint = os.getenv(f'{name}_endpoint'.upper())
        if endpoint:
            return boto3.client(name, endpoint_url=endpoint)
        # Else use the default
        return boto3.client(name)

    @staticmethod
    def escape_s3_name(name: str) -> str:
        """
        Escape the given name for S3, excluding all symbols except letters and numbers.

        Args:
            name (str): The name to be escaped.

        Returns:
            str: Escaped name.
        """
        escape_name = re.sub(r'[^a-zA-Z0-9\!\-\_\.*\'\(\) ]', '', name)
        return escape_name

    @staticmethod
    def create_directory(path: str, bucket: str) -> None:
        """
        Create a directory at the specified S3 path.

        Args:
            path (str): The path of the directory to be created.
            bucket (str): The name of the S3 bucket.
        """
        s3 = AwsS3Helper.get_client('s3')
        try:
            s3.put_object(Bucket=bucket, Key=path)
        except Exception:
            pass

    @staticmethod
    def upload_document(file: Union[str, Any], path: str, bucket: str) -> None:
        """
        Upload a document to the specified S3 path.

        Args:
            file (Union[str, Any]): The file to be uploaded. It can be a file path or a file-like object.
            path (str): The S3 path where the document will be uploaded.
            bucket (str): The name of the S3 bucket.
        """
        s3 = AwsS3Helper.get_client('s3')
        if isinstance(file, str):
            with open(file, 'rb') as fs:
                s3.upload_fileobj(fs, bucket, path)
        else:
            s3.upload_fileobj(file, bucket, path)

    @staticmethod
    def check_documents(path: str, bucket: str) -> bool:
        """
        Check if documents exist at the specified S3 path.

        Args:
            path (str): The S3 path to check.
            bucket (str): The name of the S3 bucket.

        Returns:
            bool: True if documents exist, False otherwise.
        """
        s3 = AwsS3Helper.get_client('s3')
        response = s3.list_objects_v2(Bucket=bucket, Prefix=path, Delimiter='/')
        return response['KeyCount'] > 0

    @staticmethod
    def get_documents_list(path: str, bucket: str) -> List[str]:
        """
        Get a list of documents from the specified S3 path.

        Args:
            path (str): The S3 path to retrieve documents from.
            bucket (str): The name of the S3 bucket.

        Returns:
            List[str]: List of document paths.
        """
        s3 = AwsS3Helper.get_client('s3')
        prefix_path = re.sub(r'\/$', '', path) + '/'
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix_path, Delimiter='/')
        item_list = []

        if response['KeyCount'] > 0:
            # Join CommonPrefixes and Contents as array
            if 'Contents' in response:
                item_list.extend([r.get('Key') for r in response['Contents']])
            if 'CommonPrefixes' in response:
                item_list.extend(
                    [r.get('Prefix').strip('/') for r in response['CommonPrefixes']]
                )

        return item_list

    @staticmethod
    def read_bucket_structure(bucket: str, prefix: str = '') -> List[str]:
        """
        Read the structure of the specified S3 bucket.

        Args:
            bucket (str): The name of the S3 bucket.
            prefix (str): The prefix to filter the S3 objects.

        Returns:
            List[str]: List of S3 object keys.
        """
        s3 = AwsS3Helper.get_client('s3')
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return (
            [r.get('Key') for r in response['Contents']]
            if response['KeyCount'] > 0
            else []
        )

    @staticmethod
    def write_file(content: str, path: str, bucket: str) -> bool:
        """
        Write text content to the specified S3 path.

        Args:
            content (str): The content to be written.
            path (str): The S3 path where the content will be written.
            bucket (str): The name of the S3 bucket.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        s3 = AwsS3Helper.get_client('s3')
        s3.put_object(Bucket=bucket, Key=path, Body=content)
        return True

    @staticmethod
    def write_content(content: bytes, path: str, bucket: str) -> bool:
        """
        Write binary content to the specified S3 path.

        Args:
            content (bytes): The content to be written.
            path (str): The S3 path where the content will be written.
            bucket (str): The name of the S3 bucket.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        s3 = AwsS3Helper.get_client('s3')
        s3.put_object(Bucket=bucket, Key=path, Body=content)
        return True

    @staticmethod
    def delete_file(path: str, bucket: str) -> bool:
        """
        Delete a file from the specified S3 path.

        Args:
            path (str): The S3 path of the file to be deleted.
            bucket (str): The name of the S3 bucket.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        s3 = AwsS3Helper.get_client('s3')
        s3.delete_object(Bucket=bucket, Key=path)
        return True
    
    @staticmethod
    def read_file_content(path: str, bucket: str) -> bytes:
        """
        Retrieves the content of a file stored in an S3 bucket.

        This static method connects to an S3 bucket using a predefined S3 client,
        downloads the file specified by its path within the bucket, and returns
        its content as a byte string.

        Args:
            path (str): The S3 key (path) of the file within the bucket.
            bucket (str): The name of the S3 bucket where the file is stored.

        Returns:
           bytes: The content of the file as a byte string.
        """
        s3 = AwsS3Helper.get_client('s3')
        s3_object = s3.get_object(Bucket=bucket, Key=path)
        file_content = s3_object['Body'].read()
        return file_content

    @staticmethod
    def read_file(path: str, bucket: str) -> dict:
        """
        Read a file from the specified S3 path.

        Args:
            path (str): The S3 path of the file to be read.
            bucket (str): The name of the S3 bucket.

        Returns:
            dict: The content of the file.
        """
        s3 = AwsS3Helper.get_client('s3')
        return s3.get_object(Bucket=bucket, Key=path)

    @staticmethod
    def read_json(path: str, bucket: str) -> dict:
        """
        Read a JSON file from the specified S3 path.

        Args:
            path (str): The S3 path of the JSON file to be read.
            bucket (str): The name of the S3 bucket.

        Returns:
            dict: The content of the JSON file.
        """
        s3 = AwsS3Helper.get_client('s3')
        content_obj = s3.get_object(Bucket=bucket, Key=path)
        content_str = content_obj['Body'].read().decode('utf-8')
        return json.loads(content_str)

    @staticmethod
    def write_json(data: dict, path: str, bucket: str) -> bool:
        """
        Write a JSON file to the specified S3 path.

        Args:
            data (dict): The JSON data to be written.
            path (str): The S3 path where the JSON file will be written.
            bucket (str): The name of the S3 bucket.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        s3 = AwsS3Helper.get_client('s3')
        s3.put_object(
            Bucket=bucket, Key=path, Body=json.dumps(data, default=serialize_datetime)
        )
        return True

    @staticmethod
    def is_exists(path: str, bucket: str) -> bool:
        """
        Check if a file exists at the specified S3 path.

        Args:
            path (str): The S3 path to check.
            bucket (str): The name of the S3 bucket.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        s3 = AwsS3Helper.get_client('s3')
        try:
            s3.head_object(Bucket=bucket, Key=path)
            return True
        except Exception:
            return False

    @staticmethod
    def update_json(path: str, bucket: str, update_fnc: Callable[[dict], dict]) -> dict:
        """
        Update a JSON file in S3 using the provided update function.

        Args:
            path (str): The S3 path of the JSON file to be updated.
            bucket (str): The name of the S3 bucket.
            update_fnc (Callable[[dict], dict]): The function to update the JSON data.

        Returns:
            dict: The updated JSON data.
        """
        s3 = AwsS3Helper.get_client('s3')
        content_obj = s3.get_object(Bucket=bucket, Key=path)
        content_str = content_obj['Body'].read().decode('utf-8')
        data = json.loads(content_str)
        new_data = update_fnc(data)
        new_data = {**data, **new_data}
        s3.put_object(
            Bucket=bucket,
            Key=path,
            Body=json.dumps(new_data, default=serialize_datetime),
        )
        return new_data

    @staticmethod
    def clear_folder(path: str, bucket: str) -> None:
        """
        Read the directory at the specified S3 path and delete all files.

        Args:
            path (str): The S3 path of the directory.
            bucket (str): The name of the S3 bucket.
        """
        for item in AwsS3Helper.get_documents_list(path, bucket):
            AwsS3Helper.delete_file(item, bucket)

    @staticmethod
    def format_generic_s3_path(*path_components: str) -> str:
        """
        Format a generic S3 path using the provided components.

        This method generates an S3 path based on the provided components, joining them with slashes.

        Example:
        ```python
        # Example usage
        project_name = "SampleProject"
        document_name = "ISO27001"
        category = "policies"

        # Generate S3 path for documents
        s3_document_path = AwsS3Helper.format_generic_s3_path(project_name, "documents", document_name, category)
        print(s3_document_path)
        ```

        Output:
        ```
        SampleProject/documents/ISO27001/policies
        ```

        Args:
            *path_components (str): Variable number of components to be joined in the S3 path.

        Returns:
            str: The formatted generic S3 path.
        """
        # Escape and join provided components
        escaped_components = [
            AwsS3Helper.escape_s3_name(component) for component in path_components
        ]
        s3_path = '/'.join(escaped_components)
        return s3_path

    @staticmethod
    def download_documents_with_generic_s3_path(
        components: Tuple[str, ...], bucket: str, dir_name: str
    ) -> None:
        """
        Download documents from S3 to the local directory using a generic S3 path.

        Args:
            components (Tuple[str, ...]): Components to be used for formatting the generic S3 path.
            bucket (str): The name of the S3 bucket.
            dir_name (str): The local directory where documents will be downloaded.

        Example:
        ```python
        # Example usage
        document_name = "ISO27001"
        document_category = "policies"
        project_name = "SampleProject"

        # Download documents using generic S3 path
        components = (project_name, "documents", document_name, document_category)
        AwsS3Helper.download_documents_with_generic_s3_path(components, "your-s3-bucket-name", "local-directory")
        ```
        """
        # Format S3 document path using the generic method
        document_path = AwsS3Helper.format_generic_s3_path(*components)
        document_list = AwsS3Helper.get_documents_list(document_path, bucket)

        # Create the local directory if it doesn't exist
        os.makedirs(dir_name, exist_ok=True)

        # Create S3 client outside the with statement
        s3 = AwsS3Helper.get_client('s3')

        # Download documents
        for document in document_list:
            try:
                document_obj = s3.get_object(Bucket=bucket, Key=document)
                document_data = document_obj['Body'].read()
                document_path = os.path.join(dir_name, os.path.basename(document))
                with open(document_path, 'wb') as f:
                    f.write(document_data)
            finally:
                # Close the S3 client explicitly after using it
                s3.close()