import os
import yaml
import shutil
import logging
import asyncio
from indexer import Indexer
from fastapi import FastAPI
from async_loop import loop
from aws_rds_helper import RDSHelper
from dependencies import async_queue
from contextlib import asynccontextmanager
from tenacity import retry, wait_fixed, stop_after_delay
from sqs import sqs  # Import our SQS instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@retry(wait=wait_fixed(30), stop=stop_after_delay(240))
def setup_sqs_queue():
    """
    Set up and return the SQS queue URL.

    This function retrieves the queue name from environment variables,
    creates the queue if it doesn't exist, and returns the queue URL.
    """
    queue_name = os.getenv("AWS_SQS_QUEUE")  
    logger.info(f"Setting up SQS queue: {queue_name}")
    if not queue_name:
        raise ValueError("AWS_SQS_QUEUE is not set!")
    try:
        queue_url = sqs.get_queue_url(queue_name)
        logger.info(f"Successfully set up SQS queue: {queue_url}")
        return queue_url
    except Exception as e:
        logger.error(f"Error setting up SQS queue: {str(e)}")
        raise

async def consume_sqs_messages():
    """
    Continuously poll SQS queue for messages.
    """
    queue_name = os.getenv("AWS_SQS_QUEUE")
    logger.info(f"Start SQS consuming from queue: {queue_name}")
    
    try:
        while True:
            messages = sqs.receive_messages(
                queue_name=queue_name,
                max_messages=10,  # Batch size
                wait_time=20  # Long polling timeout in seconds
            )
            
            for message in messages:
                try:
                    logger.info(f"Message received: {message['Body']}")
                    async_queue.enqueue(message['Body'].encode('utf-8'))
                    
                    # Delete message after successful processing
                    sqs.delete_message(
                        queue_name=queue_name,
                        receipt_handle=message['ReceiptHandle']
                    )
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue
            
            # Small delay to prevent tight polling if queue is empty
            if not messages:
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"Error in SQS consumer: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown process for the FastAPI app.
    """
    tasks = []
    try:
        with open('config.yml', 'r') as file:
            config = yaml.safe_load(file)
        local_path = os.environ.get("LOCAL_FILES_PATH")
        os.makedirs(local_path, exist_ok=True)
        
        # Initialize RDS helper
        rds_helper = RDSHelper(config['rds'])
        rds_helper.connect()
        
        # Initialize indexer
        indexer = Indexer(rds_helper)
        
        # Set up SQS queue
        setup_sqs_queue()
        
        # Create background tasks
        tasks.append(asyncio.create_task(consume_sqs_messages()))
        tasks.append(asyncio.create_task(loop(async_queue, indexer)))
        
        yield
        
    finally:
        # Cleanup
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error while cancelling task: {e}")
        
        # Additional cleanup
        try:
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
        except Exception as e:
            logger.error(f"Error removing local path: {e}")
            
        try:
            rds_helper.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting RDS: {e}")

def create_app() -> FastAPI:
    """
    Create and configure a FastAPI application instance, setting custom 
    paths for the OpenAPI schema and documentation, and including 
    the API router.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(
        openapi_url="/index/openapi.json",
        docs_url="/index/docs",
        lifespan=lifespan
    )
    return app

app = create_app()