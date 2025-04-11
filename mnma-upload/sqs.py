import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional, Dict, Any
import json
import os

logger = logging.getLogger(__name__)

class SQSClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'client'):
            self.region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
            self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            self.client = boto3.client(
                'sqs',
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            self.queue_urls: Dict[str, str] = {}

    def create_queue(self, queue_name: str, fifo: bool = False, **attributes) -> str:
        try:
            if fifo and not queue_name.endswith('.fifo'):
                queue_name += '.fifo'

            # Default attributes
            queue_attributes = {
                'VisibilityTimeout': '30',  # 30 seconds
                'MessageRetentionPeriod': '345600',  # 4 days
                'DelaySeconds': '0',
            }

            # Add FIFO specific attributes
            if fifo:
                queue_attributes.update({
                    'FifoQueue': 'true',
                    'ContentBasedDeduplication': 'true'
                })

            # Update with custom attributes
            queue_attributes.update(attributes)

            try:
                response = self.client.create_queue(
                    QueueName=queue_name,
                    Attributes=queue_attributes
                )
                queue_url = response['QueueUrl']
            except ClientError as e:
                if e.response['Error']['Code'] == 'QueueAlreadyExists':
                    queue_url = self.get_queue_url(queue_name)
                else:
                    raise

            self.queue_urls[queue_name] = queue_url
            return queue_url

        except Exception as e:
            logger.error(f"Error creating queue {queue_name}: {str(e)}")
            raise

    def get_queue_url(self, queue_name: str) -> str:
        if queue_name not in self.queue_urls:
            try:
                response = self.client.get_queue_url(QueueName=queue_name)
                self.queue_urls[queue_name] = response['QueueUrl']
            except ClientError as e:
                logger.error(f"Error getting queue URL for {queue_name}: {str(e)}")
                raise
        return self.queue_urls[queue_name]

    def send_message(self, queue_name: str, message: Any, 
                    message_group_id: Optional[str] = None) -> Dict:
        try:
            queue_url = self.get_queue_url(queue_name)
            
            # Convert message to string if it's not already
            if not isinstance(message, str):
                message = json.dumps(message)

            params = {
                'QueueUrl': queue_url,
                'MessageBody': message
            }

            # Add message group ID for FIFO queues
            if message_group_id:
                params['MessageGroupId'] = message_group_id

            response = self.client.send_message(**params)
            return response

        except Exception as e:
            logger.error(f"Error sending message to {queue_name}: {str(e)}")
            raise

    def receive_messages(self, queue_name: str, max_messages: int = 1, 
                        wait_time: int = 0) -> list:
        try:
            queue_url = self.get_queue_url(queue_name)
            
            response = self.client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time
            )
            
            return response.get('Messages', [])

        except Exception as e:
            logger.error(f"Error receiving messages from {queue_name}: {str(e)}")
            raise

    def delete_message(self, queue_name: str, receipt_handle: str) -> None:
        try:
            queue_url = self.get_queue_url(queue_name)
            
            self.client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )

        except Exception as e:
            logger.error(f"Error deleting message from {queue_name}: {str(e)}")
            raise

    def delete_queue(self, queue_name: str) -> None:
        try:
            queue_url = self.get_queue_url(queue_name)
            self.client.delete_queue(QueueUrl=queue_url)
            self.queue_urls.pop(queue_name, None)

        except Exception as e:
            logger.error(f"Error deleting queue {queue_name}: {str(e)}")
            raise

sqs = SQSClient()