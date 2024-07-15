"""Tasks worker configuration."""

from typing import Any, Dict, Literal

from pybotx import Bot
from saq import Queue

from app import constants
from app.caching.callback_redis_repo import CallbackRedisRepo
from app.caching.redis_client import create_redis_client
from app.logger import logger

# `saq` import its own settings and hides our module
from app.settings import settings as app_settings

SaqCtx = Dict[str, Any]


async def startup(ctx: SaqCtx) -> None:
    from app.bot.bot import get_bot  # noqa: WPS433

    redis_client = create_redis_client(
        max_connections=app_settings.REDIS_CONNECTION_POOL_SIZE
    )
    callback_repo = CallbackRedisRepo(
        redis=redis_client,
        prefix=f"{constants.BOT_PROJECT_NAME}{app_settings.CONTAINER_PREFIX}",
    )
    bot = get_bot(callback_repo)

    await bot.startup(fetch_tokens=False)

    ctx["bot"] = bot

    logger.info("Worker started")


async def shutdown(ctx: SaqCtx) -> None:
    bot: Bot = ctx["bot"]
    await bot.shutdown()

    logger.info("Worker stopped")


async def healthcheck(_: SaqCtx) -> Literal[True]:
    return True


redis_client = create_redis_client(
    max_connections=app_settings.REDIS_CONNECTION_POOL_SIZE
)
queue = Queue(
    redis_client, name=f"{constants.BOT_PROJECT_NAME}{app_settings.CONTAINER_PREFIX}"
)

settings = {
    "queue": queue,
    "functions": [healthcheck],
    "cron_jobs": [],
    "concurrency": 8,
    "startup": startup,
    "shutdown": shutdown,
}
