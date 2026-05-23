from fastapi import WebSocket
from typing import Dict
import structlog

logger = structlog.get_logger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections for audio streaming, keeping track 
    of sessions by a unique session_id.
    """
    def __init__(self):
        # Maps session_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept the websocket connection and store it."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("WebSocket connected", session_id=session_id, total_connections=len(self.active_connections))

    def disconnect(self, session_id: str):
        """Remove the connection on disconnect."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("WebSocket disconnected", session_id=session_id, total_connections=len(self.active_connections))

    async def send_personal_message(self, message: str, session_id: str):
        """Send a text message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(message)

    async def send_personal_bytes(self, data: bytes, session_id: str):
        """Send raw binary data to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_bytes(data)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error("Failed to broadcast message", session_id=session_id, error=str(e))

# Global connection manager instance
manager = ConnectionManager()
