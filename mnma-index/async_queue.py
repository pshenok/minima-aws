import asyncio

from collections import deque

class AsyncQueueDequeueInterrupted(Exception):
    """
    Exception raised when an attempt to dequeue from the AsyncQueue is interrupted.
    
    Args:
        message (str): The error message to be displayed. Defaults to "AsyncQueue dequeue was interrupted".
    """
    def __init__(self, message="AsyncQueue dequeue was interrupted"):
        self.message = message
        super().__init__(self.message)

class AsyncQueue:
    """
    An asynchronous queue implementation using deque and asyncio.Event.
    It supports enqueue and dequeue operations, with asynchronous waiting for data.

    Attributes:
        _data (deque): The underlying data structure to store queue elements.
        _presense_of_data (asyncio.Event): Event to signal the presence of data in the queue.
    """
    def __init__(self):
        self._data = deque([])
        self._presense_of_data = asyncio.Event()

    def enqueue(self, value):
        """
        Add a value to the end of the queue. If the queue was empty, set the event to indicate data presence.

        Args:
            value: The value to be added to the queue.
        """
        self._data.append(value)

        if len(self._data) == 1:
            self._presense_of_data.set()

    async def dequeue(self):
        """
        Remove and return a value from the front of the queue. Wait asynchronously for data if the queue is empty.

        Returns:
            The value from the front of the queue.

        Raises:
            AsyncQueueDequeueInterrupted: If the dequeue operation is interrupted unexpectedly.
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
        Get the current size of the queue.

        Returns:
            int: The number of elements in the queue.
        """
        result = len(self._data)
        return result

    def shutdown(self):
        """
        Set the event to indicate data presence, potentially used to wake up consumers for shutdown purposes.
        """
        self._presense_of_data.set()