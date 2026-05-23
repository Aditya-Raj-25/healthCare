import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .connection_manager import manager
from .audio_buffer import AudioBuffer
from .streaming import AudioStreamer
from .transcription_manager import transcription_manager
from .stt import process_audio_chunk
import app.events.subscribers  # Ensure legacy bridge is registered

logger = structlog.get_logger(__name__)
router = APIRouter()



@router.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket, session_id: str, language: str = "en-US"):
    """
    Production-grade WebSocket endpoint for real-time audio streaming.
    Handles binary audio chunks, buffering, and background processing loop.
    """
    # 1. Connect and initialize STT session
    await manager.connect(websocket, session_id)
    await transcription_manager.start_session(session_id, language)
    
    # 2. Setup audio buffer and streaming loop
    audio_buffer = AudioBuffer(frame_size=4096)
    streamer = AudioStreamer(session_id=session_id, buffer=audio_buffer, process_callback=process_audio_chunk)
    
    # Start background processing loop
    streamer.start()

    try:
        while True:
            # Receive data. In a real app, you might receive text (JSON) or bytes.
            # Using receive() allows us to handle both if needed.
            message = await websocket.receive()
            
            if "bytes" in message:
                chunk = message["bytes"]
                logger.debug("Received audio chunk", session_id=session_id, chunk_size=len(chunk))
                await audio_buffer.put(chunk)
            elif "text" in message:
                # Handle control messages, settings, etc.
                logger.info("Received control message", session_id=session_id, message=message["text"])
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket unexpected error", session_id=session_id, error=str(e))
    finally:
        # 3. Cleanup on disconnect
        manager.disconnect(session_id)
        await streamer.stop()
        await transcription_manager.stop_session(session_id)
