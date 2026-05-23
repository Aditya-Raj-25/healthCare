import asyncio
import structlog
from typing import Callable, Awaitable
from .audio_buffer import AudioBuffer

logger = structlog.get_logger(__name__)

class AudioStreamer:
    """
    Manages the asynchronous processing loop for an audio stream.
    Reads from the audio buffer and processes complete frames without blocking.
    """
    def __init__(self, session_id: str, buffer: AudioBuffer, process_callback: Callable[[bytes, str], Awaitable[None]]):
        self.session_id = session_id
        self.buffer = buffer
        self.process_callback = process_callback
        self._task: asyncio.Task | None = None
        self._is_running = False

    def start(self):
        """Start the background streaming loop."""
        if self._is_running:
            return
            
        self._is_running = True
        self._task = asyncio.create_task(self._streaming_loop())
        logger.info("Started audio streaming loop", session_id=self.session_id)

    async def stop(self):
        """Gracefully stop the streaming loop."""
        if not self._is_running:
            return
            
        self._is_running = False
        self.buffer.close()
        
        if self._task:
            try:
                # Wait briefly for the loop to finish processing remaining items
                await asyncio.wait_for(self._task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Streaming loop stop timed out, cancelling", session_id=self.session_id)
                self._task.cancel()
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped audio streaming loop", session_id=self.session_id)

    async def _streaming_loop(self):
        """The core loop that fetches frames from the buffer and processes them."""
        try:
            while self._is_running:
                frame = await self.buffer.get()
                if frame is None or len(frame) == 0:
                    # Sentinel value or empty queue after close
                    break
                    
                # Process the frame asynchronously
                # The process_callback should handle its own exceptions or we catch them here
                try:
                    await self.process_callback(frame, self.session_id)
                except Exception as e:
                    logger.error("Error processing audio frame", session_id=self.session_id, error=str(e))
                    
        except asyncio.CancelledError:
            logger.info("Streaming loop cancelled", session_id=self.session_id)
        except Exception as e:
            logger.error("Streaming loop unexpected error", session_id=self.session_id, error=str(e))
        finally:
            self._is_running = False
