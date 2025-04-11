import os
import logging
from aws_rds_helper import RDSHelper
from aws_s3_helper import AwsS3Helper
from sqs import sqs  # Import our SQS client

logger = logging.getLogger(__name__)

class Uploader:
    def __init__(self, rds_helper: RDSHelper):
        self.rds_helper = rds_helper
        self.queue_name = os.getenv("AWS_SQS_QUEUE") 

    def upload(self, message):
        file_path = message["file_path"]
        file_id = message["file_id"]
        user_id = message["user_id"]
        path = message["path"]
        bucket = message["bucket"]
        try:        
            # Upload to S3
            AwsS3Helper.upload_document(file_path, path, bucket)
            
            # Update RDS
            saved = self.rds_helper.insert_record(file_id, user_id, path, "uploaded")
            logger.info(f"Saved file: {saved}")
            logger.info(f"File uploaded: {path}")
            
            # Send message to SQS
            sqs.send_message(self.queue_name, message)
            
            # Clean up local file
            os.remove(file_path)
            
        except Exception as error:
            logger.error(f"Error: Could not upload file\n{error}")
            logger.error(f"Failed to upload file: {file_path}, with file_id: {file_id}")
            raise  # Re-raise to handle in caller