"""Handlers for BotX request exceptions."""

from functools import wraps
from http import HTTPStatus
from typing import Any, Callable

from fastapi.responses import JSONResponse
from pybotx import (
    UnknownBotAccountError,
    UnsupportedBotAPIVersionError,
    UnverifiedRequestError,
    build_bot_disabled_response,
    build_unverified_request_response,
)
from pybotx.constants import BOT_API_VERSION

from app.logger import logger
from app.settings import settings


def handle_exceptions(func: Callable) -> Callable:  # noqa: WPS212
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> JSONResponse:
        try:  # noqa: WPS225
            return await func(*args, **kwargs)
        except ValueError:
            error_label = "Bot command validation error"

            if settings.DEBUG:
                logger.exception(error_label)
            else:
                logger.warning(error_label)

            return JSONResponse(
                build_bot_disabled_response(error_label),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except UnknownBotAccountError as exc:
            error_label = f"No credentials for bot {exc.bot_id}"
            logger.warning(error_label)

            return JSONResponse(
                build_bot_disabled_response(error_label),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except UnsupportedBotAPIVersionError as exc:
            error_label = (
                f"Unsupported Bot API version: `{exc.version}`. "
                f"Set protocol version to `{BOT_API_VERSION}` in Admin panel."
            )
            logger.warning(error_label)

            return JSONResponse(
                build_bot_disabled_response(error_label),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except UnverifiedRequestError as exc:
            logger.warning(f"UnverifiedRequestError: {exc.args[0]}")
            return JSONResponse(
                content=build_unverified_request_response(
                    status_message=exc.args[0],
                ),
                status_code=HTTPStatus.UNAUTHORIZED,
            )

    return wrapper
