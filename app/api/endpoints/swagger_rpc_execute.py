"""Execute RPC method endpoint."""
from json import JSONDecodeError

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pybotx import Bot
from pybotx_smartapp_rpc import RPCErrorResponse, SmartApp
from pybotx_smartapp_rpc.models.request import RPCRequest
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


@router.post("/{method:str}", response_class=JSONResponse)
async def rpc_execute(
    method: str,
    request: Request,
    credentials: RPCAuthConfig = Depends(security),
    bot: Bot = bot_dependency,
) -> JSONResponse:
    """Execute RPC method."""
    bot_account, user_info = await expand_config(credentials, bot)

    try:
        method_payload = await request.json()
    except JSONDecodeError:
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
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content=rpc_response.jsonable_dict()["errors"],
        )

    return JSONResponse(
        status_code=HTTP_200_OK, content=rpc_response.jsonable_dict().get("result")
    )
