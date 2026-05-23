import structlog
from typing import Any, Dict
from app.events.bus import event_bus
from app.schemas.events import TranscriptEvent

logger = structlog.get_logger(__name__)

class TranscriptProcessor:
    """
    Parses Deepgram events and extracts the partial and final transcripts.
    Fires TranscriptEvent onto the event bus.
    """
    def __init__(self, session_id: str, language: str = "en-US"):
        self.session_id = session_id
        self.language = language
        self._current_sentence = ""

    async def process_event(self, result):
        """
        Processes a Deepgram LiveResultResponse object (SDK v3).
        """
        try:
            # SDK v3 returns an object with attributes, not a dict
            # Try object attribute access first, then fall back to dict
            if hasattr(result, 'is_final'):
                is_final = result.is_final
                try:
                    transcript = result.channel.alternatives[0].transcript
                except (AttributeError, IndexError):
                    return
            elif isinstance(result, dict):
                is_final = result.get("is_final", False)
                channel = result.get("channel", {})
                alternatives = channel.get("alternatives", [])
                if not alternatives:
                    return
                transcript = alternatives[0].get("transcript", "")
            else:
                logger.warning("Unknown event type", session_id=self.session_id, result_type=type(result).__name__)
                return

            if not transcript:
                return

            if is_final:
                logger.info("Final transcript", session_id=self.session_id, transcript=transcript)
                event = TranscriptEvent(
                    session_id=self.session_id,
                    transcript=transcript,
                    is_final=True,
                    language=self.language,
                    event_type="FINAL_TRANSCRIPT_RECEIVED"
                )
                await event_bus.publish(event)
            else:
                logger.debug("Partial transcript", session_id=self.session_id, transcript=transcript)
                event = TranscriptEvent(
                    session_id=self.session_id,
                    transcript=transcript,
                    is_final=False,
                    language=self.language,
                    event_type="PARTIAL_TRANSCRIPT_RECEIVED"
                )
                await event_bus.publish(event)

        except Exception as e:
            logger.error("Error processing transcript event", session_id=self.session_id, error=str(e), result=str(result))
