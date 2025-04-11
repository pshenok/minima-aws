import asyncio

from collections import deque

class AsyncQueueDequeueInterrupted(Exception):
    """
    Custom exception raised when a dequeue operation is interrupted unexpectedly.
    """
    def __init__(self, message="AsyncQueue dequeue was interrupted"):
        self.message = message
        super().__init__(self.message)

class AsyncQueue:
    """
    An asynchronous queue implementation using a deque for storage.
    
    This class allows for enqueueing and dequeueing items in an asynchronous 
    manner, ensuring that dequeuing waits until data is available.
    """
    def __init__(self) -> None:
        self._data = deque([])
        self._presense_of_data = asyncio.Event()

    def enqueue(self, value):
        """
        Enqueues a value to the queue.
        
        Args:
            value: The value to be added to the queue.
        """
        self._data.append(value)

        if len(self._data) == 1:
            self._presense_of_data.set()

    async def dequeue(self):
        """
        Dequeues a value from the queue asynchronously.
        
        Waits until there is data available in the queue before dequeuing.
        
        Returns:
            The dequeued value.
        
        Raises:
            AsyncQueueDequeueInterrupted: If the queue is empty after waiting.
        """
        await self._presense_of_data.wait()

        if len(self._data) < 1:
            raise AsyncQueueDequeueInterrupted("AsyncQueue was dequeue was interrupted")

        result = self._data.popleft()

        if not self._data:
            self._presense_of_data.clear()

        return result

    def size(self):
        """
        Returns the current size of the queue.
        
        Returns:
            int: The number of items in the queue.
        """
        result = len(self._data)
        return result

    def shutdown(self):
        """
        Shuts down the queue by setting the presence of data event.
        """
        self._presense_of_data.set()
