from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class AudioMessage(BaseModel):
    """
    Schema for a parsed textual message alongside the binary audio.
    Normally we receive audio as raw bytes via WebSocket, but for JSON control 
    messages (e.g. settings, interrupts), we use this schema.
    """
    event_type: str = Field(..., description="Type of the event, e.g., 'start_stream', 'end_stream', 'interrupt'")
    session_id: str = Field(..., description="Unique ID for the session")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata for the stream")

class ServerAudioEvent(BaseModel):
    """
    Schema for messages sent back to the client.
    """
    event_type: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
