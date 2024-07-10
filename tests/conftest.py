import logging
from asyncio import Task
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
)
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
import respx
from alembic import config as alembic_config
from asgi_lifespan import LifespanManager
from pybotx import (
    Bot,
    BotAccount,
    Chat,
    ChatTypes,
    File,
    IncomingMessage,
    SmartAppEvent,
    UserDevice,
    UserSender,
    lifespan_wrapper,
)
from pybotx.logger import logger
from pybotx.models.commands import BotCommand
from pybotx_smartapp_rpc import RPCArgsBaseModel, RPCResponse, SmartApp
from pybotx_smartapp_rpc.empty_args import EmptyArgs
from pybotx_smartapp_rpc.models.request import RPCRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.caching.redis_repo import RedisRepo
from app.db.sqlalchemy import db_session_factory
from app.main import get_application
from app.settings import settings
from app.smartapp.smartapp import smartapp as smartapp_rpc


@pytest.fixture(autouse=True)
def create_smartapp_files() -> None:
    path = Path("app/smartapp_files/static")
    if not path.exists():
        path.mkdir(parents=True)


@pytest.fixture
def db_migrations() -> Generator:
    alembic_config.main(argv=["upgrade", "head"])
    yield
    alembic_config.main(argv=["downgrade", "base"])


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items: List[pytest.Function]) -> None:
    # We can't use autouse, because it appends fixture to the end
    # but session from db_session fixture must be closed before migrations downgrade
    for item in items:
        item.fixturenames = ["db_migrations"] + item.fixturenames


@pytest.fixture
async def db_session(bot: Bot) -> AsyncGenerator[AsyncSession, None]:
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def redis_repo(bot: Bot) -> RedisRepo:
    return bot.state.redis_repo


def mock_authorization(
    host: str,
    bot_id: UUID,
) -> None:
    respx.get(f"https://{host}/api/v2/botx/bots/{bot_id}/token",).mock(
        return_value=httpx.Response(
            HTTPStatus.OK,
            json={
                "status": "ok",
                "result": "token",
            },
        ),
    )


@pytest.fixture
async def bot(
    respx_mock: Callable[..., Any],  # We can't apply pytest mark to fixture
) -> AsyncGenerator[Bot, None]:
    fastapi_app = get_application()
    built_bot = fastapi_app.state.bot

    for bot_account in built_bot.bot_accounts:
        mock_authorization(bot_account.host, bot_account.id)

    built_bot.answer_message = AsyncMock(return_value=uuid4())

    async with LifespanManager(fastapi_app):
        yield built_bot


@pytest.fixture
def bot_id() -> UUID:
    return settings.BOT_CREDENTIALS[0].id


@pytest.fixture
def host() -> str:
    return settings.BOT_CREDENTIALS[0].host


@pytest.fixture
def secret_key() -> str:
    return settings.BOT_CREDENTIALS[0].secret_key


@pytest.fixture
def user_huid() -> UUID:
    return UUID("cd069aaa-46e6-4223-950b-ccea42b89c06")


@pytest.fixture
def chat_id() -> UUID:
    return UUID("ed1df16f-5b5c-44c7-8c29-8a64ff86e9c9")


@pytest.fixture
def authorization_token_payload(bot_id: UUID, host: str) -> Dict[str, Any]:
    return {
        "aud": [str(bot_id)],
        "exp": datetime(year=3000, month=1, day=1).timestamp(),
        "iat": datetime(year=2000, month=1, day=1).timestamp(),
        "iss": host,
        "jti": "2uqpju31h6dgv4f41c005e1i",
        "nbf": datetime(year=2000, month=1, day=1).timestamp(),
    }


@pytest.fixture
def authorization_header(
    secret_key: str,
    authorization_token_payload: Dict[str, Any],
) -> Dict[str, str]:
    token = jwt.encode(
        payload=authorization_token_payload,
        key=secret_key,
    )
    return {"authorization": f"Bearer {token}"}


@pytest.fixture
def incoming_message_factory(
    bot_id: UUID,
    user_huid: UUID,
    host: str,
) -> Callable[..., IncomingMessage]:
    def factory(
        *,
        body: str = "",
        ad_login: Optional[str] = None,
        ad_domain: Optional[str] = None,
    ) -> IncomingMessage:
        return IncomingMessage(
            bot=BotAccount(
                id=bot_id,
                host=host,
            ),
            sync_id=uuid4(),
            source_sync_id=None,
            body=body,
            data={},
            metadata={},
            sender=UserSender(
                huid=user_huid,
                udid=uuid4(),
                ad_login=ad_login,
                ad_domain=ad_domain,
                username=None,
                is_chat_admin=True,
                is_chat_creator=True,
                device=UserDevice(
                    manufacturer=None,
                    device_name=None,
                    os=None,
                    pushes=None,
                    timezone=None,
                    permissions=None,
                    platform=None,
                    platform_package_id=None,
                    app_version=None,
                    locale=None,
                ),
            ),
            chat=Chat(
                id=uuid4(),
                type=ChatTypes.PERSONAL_CHAT,
            ),
            raw_command=None,
        )

    return factory


@pytest.fixture
async def execute_bot_command() -> Callable[[Bot, BotCommand], Awaitable[None]]:
    async def executor(
        bot: Bot,
        command: BotCommand,
    ) -> Task:  # type: ignore
        async with lifespan_wrapper(bot):
            return bot.async_execute_bot_command(command)

    return executor  # type: ignore


@pytest.fixture()
def loguru_caplog(
    caplog: pytest.LogCaptureFixture,
) -> Generator[pytest.LogCaptureFixture, None, None]:
    # https://github.com/Delgan/loguru/issues/59

    class PropogateHandler(logging.Handler):  # noqa: WPS431
        def emit(self, record: logging.LogRecord) -> None:
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropogateHandler(), format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def smartapp_event_factory(
    bot_id: UUID,
    chat_id: UUID,
    user_huid: UUID,
    host: str,
) -> Callable[..., SmartAppEvent]:
    def factory(
        *,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[List[File]] = None,
    ) -> SmartAppEvent:
        return SmartAppEvent(
            bot=BotAccount(
                id=bot_id,
                host=host,
            ),
            ref=uuid4(),
            smartapp_id=bot_id,
            data=data or {},
            opts={},
            smartapp_api_version=1,
            files=files or [],
            sender=UserSender(
                huid=user_huid,
                udid=uuid4(),
                ad_login=None,
                ad_domain=None,
                username=None,
                is_chat_admin=True,
                is_chat_creator=True,
                device=UserDevice(
                    manufacturer=None,
                    device_name=None,
                    os=None,
                    pushes=None,
                    timezone=None,
                    permissions=None,
                    platform=None,
                    platform_package_id=None,
                    app_version=None,
                    locale=None,
                ),
            ),
            chat=Chat(
                id=chat_id,
                type=ChatTypes.PERSONAL_CHAT,
            ),
            raw_command=None,
        )

    return factory


@pytest.fixture
def perform_rpc_request(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: Bot,
) -> Callable[..., Awaitable[RPCResponse]]:
    async def performer(
        *,
        method: str,
        args: Optional[RPCArgsBaseModel] = None,
        files: Optional[List[File]] = None,
    ) -> RPCResponse:
        if not args:
            args = EmptyArgs()

        event = smartapp_event_factory(files=files)

        smartapp = SmartApp(bot, event.bot.id, event.chat.id, event)
        rpc_request = RPCRequest(method=method, type="smartapp_rpc", params=args.dict())

        return await smartapp_rpc._router.perform_rpc_request(  # noqa: WPS437
            smartapp,
            rpc_request,
        )

    return performer
