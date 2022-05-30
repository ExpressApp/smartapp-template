from typing import Awaitable, Callable

import pytest
from pybotx_smartapp_rpc import RPCErrorResponse, RPCResponse, RPCResultResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.caching.redis_repo import RedisRepo
from app.db.record.repo import RecordRepo
from app.schemas.record import Record
from app.smartapp.rpc_methods.common import EchoArgs


async def test_sum_method(
    perform_rpc_request: Callable[..., Awaitable[RPCResponse]],
) -> None:
    # - Arrange -
    args = EchoArgs(text="Test text")

    # - Act -
    response = await perform_rpc_request(method="test:echo", args=args)

    # - Assert -
    assert isinstance(response, RPCResultResponse)
    assert response.result == "Test text"


async def test_fail_method(
    perform_rpc_request: Callable[..., Awaitable[RPCResponse]],
    loguru_caplog: pytest.LogCaptureFixture,
) -> None:
    # - Act -
    response = await perform_rpc_request(method="test:fail")

    # - Assert -
    assert isinstance(response, RPCErrorResponse)
    assert response.errors[0].reason == "Internal error"
    assert response.errors[0].id == "VALUEERROR"
    assert "Test smart_log output" in loguru_caplog.text


async def test_redis_method(
    perform_rpc_request: Callable[..., Awaitable[RPCResponse]],
    redis_repo: RedisRepo,
) -> None:
    # - Act -
    response = await perform_rpc_request(method="test:redis")

    # - Assert -
    assert isinstance(response, RPCResultResponse)
    assert await redis_repo.rget("test_key") == "test_value"
    assert await redis_repo.get("test_key") is None


async def test_db_method(
    perform_rpc_request: Callable[..., Awaitable[RPCResponse]],
    db_session: AsyncSession,
) -> None:
    # - Arrange -
    record_repo = RecordRepo(db_session)

    # - Act -
    response = await perform_rpc_request(method="test:db")

    # - Assert -
    assert isinstance(response, RPCResultResponse)
    assert await record_repo.get(record_id=1) == Record(
        id=1, record_data="test 1 (updated)"
    )
    assert await record_repo.get_or_none(record_id=2) is None
    assert await record_repo.filter_by_record_data(
        record_data="test not unique data"
    ) == [
        Record(id=3, record_data="test not unique data"),
        Record(id=4, record_data="test not unique data"),
    ]
    assert await record_repo.get_all() == [
        Record(id=1, record_data="test 1 (updated)"),
        Record(id=3, record_data="test not unique data"),
        Record(id=4, record_data="test not unique data"),
    ]


async def test_git_commit_sha_method(
    perform_rpc_request: Callable[..., Awaitable[RPCResponse]],
) -> None:
    # - Act -
    response = await perform_rpc_request(method="debug:git-commit-sha")

    # - Assert -
    assert isinstance(response, RPCResultResponse)
    assert response.result == "<undefined>"
