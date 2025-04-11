import os
import api
import yaml
import shutil
import asyncio
import logging
from async_loop import loop
from fastapi import FastAPI
from uploader import Uploader
from dependencies import async_queue
from dependencies import rds_helper
from aws_s3_helper import AwsS3Helper
from contextlib import asynccontextmanager
from tenacity import retry, wait_fixed, stop_after_delay
from sqs import sqs  # Import our SQS instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("upload")

@retry(wait=wait_fixed(5), stop=stop_after_delay(60))
def setup_sqs_queue():
    """
    Sets up and returns the SQS queue.
    
    This function retrieves the queue name from environment variables,
    creates the queue if it doesn't exist, and returns the queue URL.
    The function will retry on failure, waiting 5 seconds between attempts,
    and will stop trying after 60 seconds.
    """
    logger.info("Setting up SQS queue")
    queue_name = os.getenv("AWS_SQS_QUEUE")
    try:
        # Create queue with default settings
        queue_url = sqs.get_queue_url(queue_name)
        logger.info(f"Successfully set up SQS queue: {queue_url}")
        return queue_url
    except Exception as e:
        logger.error(f"Error setting up SQS queue: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifespan of the FastAPI application.
    """
    # Get environment variables
    bucket = os.getenv("AWS_BUCKET_NAME")
    s3_path = os.getenv("AWS_FILES_PATH")
    local_path = os.getenv("LOCAL_FILES_PATH")

    try:
        # Initialize RDS and create table
        rds_helper.connect()
        rds_helper.create_table()

        # Set up AWS S3
        AwsS3Helper.create_directory(bucket, s3_path)
        
        # Create local directory
        os.makedirs(local_path, exist_ok=True)

        # Initialize uploader
        uploader = Uploader(rds_helper)

        # Set up SQS queue
        setup_sqs_queue()

        # Start processing task
        task = asyncio.create_task(loop(async_queue, uploader))

        yield

        # Cleanup
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        
        # Properly cancel and await the task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        async_queue.shutdown()
        rds_helper.disconnect()

    except Exception as e:
        logger.error(f"Error in lifespan: {e}")
        raise

def create_app() -> FastAPI:
    """
    Create and configure a FastAPI application instance, setting custom 
    paths for the OpenAPI schema and documentation, and including 
    the API router.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(
        openapi_url="/upload/openapi.json",
        docs_url="/upload/docs",
        lifespan=lifespan
    )
    app.include_router(api.router)
    return app

# Create the FastAPI application
app = create_app()