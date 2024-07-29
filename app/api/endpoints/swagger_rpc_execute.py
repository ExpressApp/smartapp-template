"""Execute RPC method endpoint."""
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pybotx import Bot
from pybotx_smartapp_rpc import RPCErrorResponse, SmartApp
from pybotx_smartapp_rpc.models.request import RPCRequest
from pydantic.json import pydantic_encoder
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from app.api.dependencies.bot import bot_dependency
from app.services.execute_rpc import (
    RPCAuthConfig,
    event_factory,
    expand_config,
    security,
)
from app.smartapp.smartapp import smartapp as smartapp_rpc

router = APIRouter(include_in_schema=False)


@router.post("/{method:str}", response_class=Response)
async def rpc_execute(
    method: str,
    request: Request,
    credentials: RPCAuthConfig = Depends(security),
    bot: Bot = bot_dependency,
) -> Response:
    """Execute RPC method."""
    bot_account, user_info = await expand_config(credentials, bot)

    try:
        method_payload = await request.json()
    except json.JSONDecodeError:
        method_payload = {}

    event = event_factory(
        method,
        method_payload,
        bot_account,
        user_info,
        credentials.sender_udid,
        credentials.chat_id,
    )

    smartapp = SmartApp(bot, event.bot.id, event.chat.id, event)
    rpc_request = RPCRequest(method=method, type="smartapp_rpc", params=method_payload)

    rpc_response = await smartapp_rpc._router.perform_rpc_request(  # noqa: WPS437
        smartapp, rpc_request
    )
    if isinstance(rpc_response, RPCErrorResponse):
        return Response(
            status_code=HTTP_400_BAD_REQUEST,
            headers={"Content-Type": "application/json"},
            content=json.dumps(rpc_response.errors, default=pydantic_encoder),
        )

    return Response(
        status_code=HTTP_200_OK,
        headers={"Content-Type": "application/json"},
        content=json.dumps(rpc_response.result, default=pydantic_encoder),
    )
