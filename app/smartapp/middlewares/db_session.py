"""Middleware for creating db_session per-request."""

from typing import Callable

from pybotx_smartapp_rpc import RPCArgsBaseModel, RPCResponse, SmartApp

from app.db.sqlalchemy import db_session_factory


async def db_session_middleware(
    smartapp: SmartApp, rpc_arguments: RPCArgsBaseModel, call_next: Callable
) -> RPCResponse:
    async with db_session_factory() as db_session:
        smartapp.state.db_session = db_session

        response = await call_next(smartapp, rpc_arguments)
        await db_session.commit()

    return response
