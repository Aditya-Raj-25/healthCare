from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.core.database import get_db_session
from app.core.redis import get_redis

router = APIRouter()

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """
    Health check endpoint to verify API, Database, and Redis connectivity.
    """
    health_status = {
        "status": "healthy",
        "database": "unhealthy",
        "redis": "unhealthy"
    }

    try:
        # Simple DB check
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"

    try:
        # Simple Redis check
        await redis.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"

    return health_status
