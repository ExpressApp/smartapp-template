"""Middlewares to log all RPC requests using smart logger wrapper."""
from typing import Any, Dict, Optional

from pybotx_smart_logger import wrap_smart_logger
from pybotx_smartapp_rpc import HandlerWithArgs, RPCArgsBaseModel, RPCResponse, SmartApp

from app.services.log_formatters import format_smartapp_event
from app.settings import settings


def is_enabled_debug(smartapp: SmartApp) -> bool:
    if smartapp.event is None:
        return False
    return settings.DEBUG


async def smart_logger_middleware(
    smartapp: SmartApp, rpc_arguments: RPCArgsBaseModel, call_next: HandlerWithArgs
) -> RPCResponse:
    raw_command: Optional[Dict[str, Any]] = None
    if smartapp.event:
        raw_command = smartapp.event.raw_command
    async with wrap_smart_logger(
        log_source="SmartApp RPC handler",
        context_func=lambda: format_smartapp_event(raw_command),
        debug=is_enabled_debug(smartapp),
    ):
        return await call_next(smartapp, rpc_arguments)
