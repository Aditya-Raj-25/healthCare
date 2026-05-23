from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone

class EventBase(BaseModel):
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str

class TranscriptEvent(EventBase):
    transcript: str
    is_final: bool
    language: str = "en-US"
    confidence: Optional[float] = None
    event_type: Literal["PARTIAL_TRANSCRIPT_RECEIVED", "FINAL_TRANSCRIPT_RECEIVED"]

class SystemErrorEvent(EventBase):
    error_message: str
    event_type: Literal["SYSTEM_ERROR"] = "SYSTEM_ERROR"
