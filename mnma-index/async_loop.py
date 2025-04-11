import json
import asyncio
import logging
from indexer import Indexer
from async_queue import AsyncQueue
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor()

async def loop(async_queue: AsyncQueue, indexer: Indexer):
    """
    Continuously process files from the async_queue, index them, and store vectors into vectors database.
    If the queue is empty, it sleeps for a short period before checking again.

    Args:
        async_queue (AsyncQueue): The queue to dequeue file paths from.
        indexer (Indexer): The indexer to process file and store vectors to database.
        rds_helper (RDSHelper): The RDSHelper to update the status of the files.

    Raises:
        Exception: If an error occurs during the file processing or metadata storage.
    """
    while True:
        if async_queue.size() == 0:
            await asyncio.sleep(0.1)
            continue
        try:
            message = await async_queue.dequeue()
            logger.info(f"Processing message: {message}")
            parsed = json.loads(message)
            loop = asyncio.get_running_loop()
            loop.run_in_executor(executor, indexer.index_file, parsed)
        except Exception as e:
            logger.error(f"Error in loop: {e}")
            logger.error(f"Failed to process message: {message}")