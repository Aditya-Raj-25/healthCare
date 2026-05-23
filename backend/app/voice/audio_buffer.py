import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

class AudioBuffer:
    """
    An asynchronous buffer for accumulating binary audio chunks.
    Allows for collecting small network frames into larger, processable frames.
    """
    def __init__(self, frame_size: int = 4096):
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._buffer = bytearray()
        self.frame_size = frame_size
        self._is_closed = False

    async def put(self, chunk: bytes):
        """Push each incoming chunk immediately to the queue for low-latency streaming."""
        if self._is_closed:
            return
        if chunk:
            await self.queue.put(chunk)

    async def get(self) -> Optional[bytes]:
        """Wait for and retrieve the next audio frame from the queue."""
        if self._is_closed and self.queue.empty():
            return None
        
        try:
            # Wait for the next item in the queue
            frame = await self.queue.get()
            return frame
        except asyncio.CancelledError:
            return None

    def close(self):
        """Close the buffer, ensuring any remaining data is flushed."""
        self._is_closed = True
        if len(self._buffer) > 0:
            # Push whatever is remaining as a final frame
            try:
                self.queue.put_nowait(bytes(self._buffer))
            except asyncio.QueueFull:
                pass
            self._buffer.clear()
        
        # Put a sentinel value or rely on the empty queue check
        try:
            self.queue.put_nowait(b"") # Empty byte string as sentinel
        except asyncio.QueueFull:
            pass

    @property
    def is_empty(self) -> bool:
        return self.queue.empty() and len(self._buffer) == 0
