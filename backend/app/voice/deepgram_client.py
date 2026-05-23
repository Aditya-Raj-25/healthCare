import asyncio
import structlog
import json
from typing import Optional
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)
from app.core.config import settings
from .transcript_processor import TranscriptProcessor

logger = structlog.get_logger(__name__)

class DeepgramStreamingClient:
    """
    Manages a single Deepgram LiveClient connection for a specific session.
    """
    def __init__(self, session_id: str, transcript_processor: TranscriptProcessor, language: str = "en-US"):
        self.session_id = session_id
        self.processor = transcript_processor
        self.language = language
        self._keep_alive_task = None
        
        # Configure Deepgram
        self.dg_client = DeepgramClient(settings.DEEPGRAM_API_KEY)
        
        self.live_client = None
        self._is_connected = False
        
    async def connect(self):
        """Initializes the connection to Deepgram."""
        if self._is_connected:
            return
            
        if not settings.DEEPGRAM_API_KEY:
            logger.error("DEEPGRAM_API_KEY is not set. STT will fail.")
            return

        try:
            self.live_client = self.dg_client.listen.asyncwebsocket.v("1")

            # Setup event handlers
            self.live_client.on(LiveTranscriptionEvents.Transcript, self._on_message)
            self.live_client.on(LiveTranscriptionEvents.Error, self._on_error)
            self.live_client.on(LiveTranscriptionEvents.Close, self._on_close)

            options = LiveOptions(
                model="nova-2",
                language=self.language,
                smart_format=True,
                interim_results=True,
                endpointing=2500 # Wait 2.5 seconds of silence before marking final
            )
            
            # Use run_in_executor if the start method blocks, but asyncwebsocket should be async
            if await self.live_client.start(options) is False:
                logger.error("Failed to connect to Deepgram", session_id=self.session_id)
                return

            self._is_connected = True
            logger.info("Connected to Deepgram STT", session_id=self.session_id, language=self.language)
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
            
        except Exception as e:
            logger.error("Error setting up Deepgram connection", session_id=self.session_id, error=str(e))

    async def _on_message(self, *args, **kwargs):
        """Handler for incoming transcript events from Deepgram SDK v3."""
        result = kwargs.get("result")
        if not result and len(args) > 1:
            result = args[1]

        if result is None:
            return

        logger.debug("Deepgram raw event", session_id=self.session_id, result_type=type(result).__name__)
        await self.processor.process_event(result)

    async def _on_error(self, *args, **kwargs):
        logger.error("Deepgram STT Error", session_id=self.session_id, args=args, kwargs=kwargs)

    async def _on_close(self, *args, **kwargs):
        self._is_connected = False
        logger.info("Deepgram connection closed", session_id=self.session_id)

    async def send_audio(self, chunk: bytes):
        """Sends raw audio bytes to Deepgram. Reconnects if the connection was dropped."""
        if not self._is_connected or not self.live_client:
            logger.info("Deepgram connection dropped. Attempting to reconnect...", session_id=self.session_id)
            await self.connect()
            if not self._is_connected:
                logger.error("Failed to reconnect to Deepgram.", session_id=self.session_id)
                return
            
        try:
            # Send method from SDK
            await self.live_client.send(chunk)
        except Exception as e:
            logger.error("Failed to send audio to Deepgram", session_id=self.session_id, error=str(e))
            
    async def _keep_alive_loop(self):
        while self._is_connected and self.live_client:
            await asyncio.sleep(5)
            if self._is_connected and self.live_client:
                try:
                    await self.live_client.keep_alive()
                except Exception as e:
                    logger.debug("KeepAlive failed", session_id=self.session_id, error=str(e))

    async def disconnect(self):
        """Cleanly disconnects the Deepgram client."""
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            
        if self._is_connected and self.live_client:
            try:
                await self.live_client.finish()
            except Exception as e:
                logger.error("Error closing Deepgram connection", session_id=self.session_id, error=str(e))
            finally:
                self._is_connected = False
                logger.info("Disconnected Deepgram STT", session_id=self.session_id)
