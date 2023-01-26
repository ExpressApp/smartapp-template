"""Handlers for default smartapp rpc methods."""
from os import environ

from pybotx_smart_logger import smart_log
from pybotx_smartapp_rpc import RPCArgsBaseModel, RPCResultResponse, RPCRouter, SmartApp

from app.db.record.repo import RecordRepo
from app.smartapp.middlewares.db_session import db_session_middleware

rpc = RPCRouter()


class EchoArgs(RPCArgsBaseModel):
    text: str


@rpc.method("test:echo")
async def test_sum(
    smartapp: SmartApp, rpc_arguments: EchoArgs
) -> RPCResultResponse[str]:
    return RPCResultResponse(rpc_arguments.text)


@rpc.method("test:fail")
async def test_fail(smartapp: SmartApp) -> RPCResultResponse[str]:
    smart_log("Test smart_log output")
    raise ValueError


@rpc.method("test:redis")
async def test_redis(smartapp: SmartApp) -> RPCResultResponse[str]:
    # This test just for coverage
    # Better to assert bot answers instead of using direct DB/Redis access

    redis_repo = smartapp.bot.state.redis_repo

    await redis_repo.set("test_key", "test_value")

    return RPCResultResponse("")


@rpc.method("test:db", middlewares=[db_session_middleware])
async def test_db(smartapp: SmartApp) -> RPCResultResponse[str]:
    # This test just for coverage
    # Better to assert bot answers instead of using direct DB/Redis access

    # add text to history
    # example of using database
    record_repo = RecordRepo(smartapp.state.db_session)

    await record_repo.create(record_data="test 1")
    await record_repo.update(record_id=1, record_data="test 1 (updated)")

    await record_repo.create(record_data="test 2")
    await record_repo.delete(record_id=2)

    await record_repo.create(record_data="test not unique data")
    await record_repo.create(record_data="test not unique data")

    return RPCResultResponse("")


@rpc.method("debug:git-commit-sha")
async def test_redis_callback_repo(smartapp: SmartApp) -> RPCResultResponse[str]:
    return RPCResultResponse(environ.get("GIT_COMMIT_SHA", "<undefined>"))
