from async_queue import AsyncQueue

# Create a shared instance of AsyncQueue.
# This shared instance will be used across different parts of the application.
# Ensure that this shared object is managed carefully to prevent concurrency issues.
async_queue = AsyncQueue()