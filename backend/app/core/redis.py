from redis.asyncio import Redis, ConnectionPool
from .config import settings
import structlog

logger = structlog.get_logger(__name__)

class RedisClient:
    def __init__(self):
        self.pool = None
        self.client = None

    async def connect(self):
        self.pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.client = Redis(connection_pool=self.pool)
        logger.info("Connected to Redis")

    async def disconnect(self):
        if self.pool:
            await self.pool.disconnect()
        logger.info("Disconnected from Redis")

redis_client = RedisClient()

async def get_redis() -> Redis:
    if not redis_client.client:
        await redis_client.connect()
    return redis_client.client
