from typing import Dict
import structlog
from .deepgram_client import DeepgramStreamingClient
from .transcript_processor import TranscriptProcessor

logger = structlog.get_logger(__name__)

class TranscriptionManager:
    """
    Manages active STT sessions, mapping session_ids to their Deepgram clients.
    """
    def __init__(self):
        self.active_sessions: Dict[str, DeepgramStreamingClient] = {}

    async def start_session(self, session_id: str, language: str = "en-US") -> DeepgramStreamingClient:
        """Initializes a new STT session."""
        if session_id in self.active_sessions:
            logger.warning("Session already exists, stopping old one", session_id=session_id)
            await self.stop_session(session_id)

        processor = TranscriptProcessor(session_id, language)
        dg_client = DeepgramStreamingClient(session_id, processor, language)
        
        await dg_client.connect()
        self.active_sessions[session_id] = dg_client
        return dg_client

    async def get_session(self, session_id: str) -> DeepgramStreamingClient | None:
        """Retrieves an active session."""
        return self.active_sessions.get(session_id)

    async def stop_session(self, session_id: str):
        """Stops and cleans up an STT session."""
        client = self.active_sessions.pop(session_id, None)
        if client:
            await client.disconnect()

transcription_manager = TranscriptionManager()
