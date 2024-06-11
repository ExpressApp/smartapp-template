"""Endpoints for communication with botx."""

from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pybotx import (
    Bot,
    BotXMethodCallbackNotFoundError,
    UnknownBotAccountError,
    UnverifiedRequestError,
    build_bot_disabled_response,
    build_command_accepted_response,
    build_unverified_request_response,
)

from app.api.dependencies.bot import bot_dependency
from app.api.exceptions.botx import handle_exceptions
from app.logger import logger

router = APIRouter()


@router.post("/command")
@handle_exceptions
async def command_handler(request: Request, bot: Bot = bot_dependency) -> JSONResponse:
    """Receive commands from users. Max timeout - 5 seconds."""
    bot.async_execute_raw_bot_command(
        await request.json(),
        request_headers=request.headers,
    )
    return JSONResponse(
        build_command_accepted_response(), status_code=HTTPStatus.ACCEPTED
    )


@router.post("/smartapp/request")
@handle_exceptions
async def sync_smartapp_request_handler(
    request: Request, bot: Bot = bot_dependency
) -> JSONResponse:
    response = await bot.sync_execute_raw_smartapp_request(
        await request.json(),
        request_headers=request.headers,
    )
    return JSONResponse(response.jsonable_dict(), status_code=HTTPStatus.OK)


@router.get("/status")
async def status_handler(request: Request, bot: Bot = bot_dependency) -> JSONResponse:
    """Show bot status and commands list."""

    try:
        status = await bot.raw_get_status(
            dict(request.query_params),
            request_headers=request.headers,
        )
    except UnknownBotAccountError as exc:
        error_label = f"Unknown bot_id: {exc.bot_id}"
        logger.warning(exc)
        return JSONResponse(
            build_bot_disabled_response(error_label),
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )
    except ValueError:
        error_label = "Invalid params"
        logger.warning(error_label)
        return JSONResponse(
            build_bot_disabled_response(error_label), status_code=HTTPStatus.BAD_REQUEST
        )
    except UnverifiedRequestError as exc:
        logger.warning(f"UnverifiedRequestError: {exc.args[0]}")
        return JSONResponse(
            content=build_unverified_request_response(
                status_message=exc.args[0],
            ),
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    return JSONResponse(status)


@router.post("/notification/callback")
async def callback_handler(request: Request, bot: Bot = bot_dependency) -> JSONResponse:
    """Process BotX methods callbacks."""

    try:
        await bot.set_raw_botx_method_result(
            await request.json(),
            verify_request=False,
        )
    except BotXMethodCallbackNotFoundError as exc:
        error_label = f"Unexpected callback with sync_id: {exc.sync_id}"
        logger.warning(error_label)

        return JSONResponse(
            build_bot_disabled_response(error_label),
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    return JSONResponse(
        build_command_accepted_response(),
        status_code=HTTPStatus.ACCEPTED,
    )
