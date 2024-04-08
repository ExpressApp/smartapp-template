"""Application with configuration for events, routers and middleware."""

from functools import partial
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pybotx import Bot, CallbackRepoProto
from redis import asyncio as aioredis

from app.api.routers import router
from app.bot.bot import get_bot
from app.caching.redis_repo import RedisRepo
from app.constants import BOT_PROJECT_NAME
from app.db.sqlalchemy import build_db_session_factory, close_db_connections
from app.services.openapi import custom_openapi
from app.services.static_files import StaticFilesCustomHeaders
from app.settings import settings
from app.smartapp.smartapp import smartapp


async def startup(bot: Bot) -> None:
    # -- Bot --
    await bot.startup()

    # -- Database --
    bot.state.db_session_factory = await build_db_session_factory()

    # -- Redis --
    bot.state.redis = aioredis.from_url(settings.REDIS_DSN)
    bot.state.redis_repo = RedisRepo(redis=bot.state.redis, prefix=BOT_PROJECT_NAME)


async def shutdown(bot: Bot) -> None:
    # -- Bot --
    await bot.shutdown()

    # -- Redis --
    await bot.state.redis.aclose()

    # -- Database --
    await close_db_connections()


def get_application(
    add_internal_error_handler: bool = True,
    callback_repo: Optional[CallbackRepoProto] = None,
) -> FastAPI:
    """Create configured server application instance."""

    bot = get_bot(callback_repo)

    application = FastAPI(
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    application.state.bot = bot

    application.add_event_handler("startup", partial(startup, bot))
    application.add_event_handler("shutdown", partial(shutdown, bot))

    application.include_router(router)

    # mount static
    application.mount(
        "/smartapp_files",
        StaticFilesCustomHeaders(
            directory="app/smartapp_files",
            headers={
                "cache-control": "no-store, no-cache, must-revalidate",
                "expires": "-1",
            },
        ),
        name="smartapp_files",
    )

    def get_custom_openapi() -> Dict[str, Any]:  # noqa: WPS430
        return custom_openapi(
            title=BOT_PROJECT_NAME,
            version="0.1.0",
            fastapi_routes=application.routes,
            rpc_router=smartapp.router,
            openapi_version="3.0.2",
        )

    application.openapi = get_custom_openapi  # type: ignore

    return application
