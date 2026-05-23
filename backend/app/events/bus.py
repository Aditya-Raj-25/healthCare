import asyncio
import structlog
from typing import Callable, Awaitable, Dict, List
from app.schemas.events import EventBase

logger = structlog.get_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[[EventBase], Awaitable[None]]

class EventBus:
    """
    Async In-Memory Event Bus for the Orchestration System.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed to event", event_type=event_type, handler=handler.__name__)

    async def publish(self, event: EventBase):
        event_type = event.event_type
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug("No subscribers for event", event_type=event_type, session_id=event.session_id)
            return

        logger.info("Publishing event", event_type=event_type, session_id=event.session_id, handlers=len(handlers))
        
        # Fire-and-forget execution of handlers so the publisher isn't blocked
        for handler in handlers:
            asyncio.create_task(self._safe_execute(handler, event))

    async def _safe_execute(self, handler: EventHandler, event: EventBase):
        try:
            await handler(event)
        except Exception as e:
            logger.error("Error in event handler", 
                         event_type=event.event_type, 
                         handler=handler.__name__, 
                         session_id=event.session_id, 
                         error=str(e))

event_bus = EventBus()
