"""Create redis client."""
from redis import asyncio as aioredis

from app.settings import settings


def create_redis_client(max_connections: int = 15) -> aioredis.Redis:
    redis_client = aioredis.from_url(settings.REDIS_DSN)
    pool = aioredis.BlockingConnectionPool(
        max_connections=max_connections,  # noqa: WPS432
        **redis_client.connection_pool.connection_kwargs
    )
    redis_client.connection_pool = pool
    return redis_client
