import structlog
from typing import Awaitable, Callable
from .transcription_manager import transcription_manager

logger = structlog.get_logger(__name__)

async def process_audio_chunk(frame: bytes, session_id: str):
    """
    Called by AudioStreamer for every collected audio frame.
    Pushes the frame to the active Deepgram STT session.
    """
    client = await transcription_manager.get_session(session_id)
    if client:
        await client.send_audio(frame)
    else:
        logger.warning("No STT session found for audio frame", session_id=session_id)

import asyncio
from app.llm.llm_client import process_transcript_with_llm

async def handle_final_transcript(transcript: str, session_id: str):
    """
    Callback fired by the TranscriptProcessor when a final transcript is ready.
    This acts as the bridge to the AI Orchestrator.
    """
    logger.info("Final transcript forwarded to orchestrator", session_id=session_id, transcript=transcript)
    # Send the transcript to the agent's LLM in the background so it doesn't block STT events
    asyncio.create_task(process_transcript_with_llm(session_id, transcript))
