import os
import asyncio
import logging
import json
from uploader import Uploader
from async_queue import AsyncQueue
from concurrent.futures import ThreadPoolExecutor
from sqs import sqs 

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor()

def send_sqs_message(message: dict, queue_name: str):
    """
    Send a message to SQS queue.
    """
    try:
        response = sqs.send_message(queue_name, json.dumps(message))
        logger.info(f"Message sent to SQS. MessageId: {response.get('MessageId')}")
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {str(e)}")
        raise

class DummyProducer:
    """Dummy producer to satisfy the Uploader's interface"""
    def send(self, *args, **kwargs):
        pass

class UploaderWithSQS:
    
    def __init__(self, uploader: Uploader):
        self.uploader = uploader
        self.queue_name = os.getenv("AWS_SQS_QUEUE")

    def upload(self, message: dict):
        """
        Upload file and send message to SQS.
        """
        try:
            # Pass dummy producer to satisfy the method signature
            self.uploader.upload(message)
            
            # Send message to SQS
            send_sqs_message(message, self.queue_name)
            
        except Exception as e:
            logger.error(f"Error in upload: {str(e)}")
            raise

async def loop(async_queue: AsyncQueue, uploader: Uploader):
    """
    Continuously process files from the async_queue.
    """
    sqs_uploader = UploaderWithSQS(uploader)
    
    while True:
        if async_queue.size() == 0:
            await asyncio.sleep(0.1)
            continue
        
        try:
            message = await async_queue.dequeue()
            file_id = message["file_id"]
            user_id = message["user_id"]
            file_path = message["file_path"]
            logger.info(f"User with id: {user_id} uploaded file with id: {file_id}, path: {file_path}")

            bucket = os.environ.get("AWS_BUCKET_NAME")
            path = os.environ.get("AWS_FILES_PATH")

            file_name = os.path.basename(file_path)
            path = f"{path}/{file_name}"
            loop = asyncio.get_running_loop()
            
            message = {
                "user_id": user_id,
                "file_id": file_id,
                "file_path": file_path,
                "bucket": bucket,
                "path": path,
            }
            
            await loop.run_in_executor(executor, sqs_uploader.upload, message)
            
        except Exception as e:
            logger.error(f"Error in loop: {e}")
            logger.error(f"Failed to upload file: {file_path}")