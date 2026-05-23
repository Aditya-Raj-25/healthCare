import structlog
import json
import asyncio
from app.events.bus import event_bus
from app.schemas.events import TranscriptEvent
from app.voice.connection_manager import manager
from app.llm.llm_client import process_transcript_with_llm

logger = structlog.get_logger(__name__)

async def legacy_transcript_bridge(event: TranscriptEvent):
    """
    Bridges Event Bus messages back to the WebSocket for the frontend,
    and forwards final transcripts to the legacy LLM orchestrator temporarily
    until the new Orchestrator layer is built.
    """
    try:
        # Send to WebSocket
        ws_event_type = "final_transcript" if event.is_final else "partial_transcript"
        await manager.send_personal_message(
            json.dumps({"event_type": ws_event_type, "message": event.transcript}), 
            event.session_id
        )
        
        # Trigger LLM on final transcript (legacy bridge)
        if event.is_final:
            logger.info("Triggering legacy LLM orchestrator from Event Bus", session_id=event.session_id)
            asyncio.create_task(process_transcript_with_llm(event.session_id, event.transcript, event.language))
            
    except Exception as e:
        logger.error("Error in legacy transcript bridge", error=str(e), session_id=event.session_id)

# Register the subscribers
event_bus.subscribe("PARTIAL_TRANSCRIPT_RECEIVED", legacy_transcript_bridge)
event_bus.subscribe("FINAL_TRANSCRIPT_RECEIVED", legacy_transcript_bridge)
logger.info("Registered legacy transcript bridge subscribers")
