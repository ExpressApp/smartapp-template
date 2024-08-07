"""Application with configuration for events, routers and middleware."""

from functools import partial
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pybotx import Bot, CallbackRepoProto

from app.api.routers import router
from app.bot.bot import get_bot
from app.caching.redis_client import create_redis_client
from app.caching.redis_repo import RedisRepo
from app.constants import BOT_PROJECT_NAME
from app.db.sqlalchemy import close_db_connections
from app.services.openapi import custom_openapi, get_project_version
from app.services.static_files import StaticFilesCustomHeaders
from app.settings import settings
from app.smartapp.smartapp import smartapp


async def startup(bot: Bot) -> None:
    # -- Bot --
    await bot.startup()

    # -- Redis --
    redis_client = create_redis_client(
        max_connections=settings.REDIS_CONNECTION_POOL_SIZE
    )
    bot.state.redis_repo = RedisRepo(
        redis=redis_client, prefix=f"{BOT_PROJECT_NAME}{settings.CONTAINER_PREFIX}"
    )
    bot.state.redis = redis_client


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
            version=get_project_version(),
            fastapi_routes=application.routes,
            rpc_router=smartapp.router,
            openapi_version="3.0.2",
        )

    application.openapi = get_custom_openapi  # type: ignore

    return application
