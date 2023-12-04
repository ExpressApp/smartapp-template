import re
from typing import Any, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.security import APIKeyHeader
from pybotx import (
    Bot,
    BotAccount,
    Chat,
    ChatTypes,
    SmartAppEvent,
    UserDevice,
    UserFromSearch,
    UserKinds,
    UserNotFoundError,
    UserSender,
)
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from app.settings import settings


class RPCAuthConfig(BaseModel):
    bot_id: UUID = settings.BOT_CREDENTIALS[0].id
    sender_huid: UUID = uuid4()
    sender_udid: UUID = uuid4()
    chat_id: UUID = uuid4()


async def expand_config(
    config: RPCAuthConfig, bot: Bot
) -> Tuple[BotAccount, UserFromSearch]:
    bot_account = [bot for bot in bot.bot_accounts if bot.id == config.bot_id]
    if not bot_account:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Bot with id {config.bot_id} not found",
        )
    try:
        user_info = await bot.search_user_by_huid(
            bot_id=bot_account[0].id, huid=config.sender_huid
        )
    except UserNotFoundError:
        user_info = UserFromSearch(
            huid=config.sender_huid,
            ad_login=None,
            ad_domain=None,
            username="Username",
            company=None,
            company_position=None,
            department=None,
            emails=[],
            other_id=None,
            user_kind=UserKinds.CTS_USER,
        )

    return bot_account[0], user_info


def event_factory(
    method_name: str,
    payload: dict[str, Any],
    bot_account: BotAccount,
    user_info: UserFromSearch,
    user_udid: UUID,
    chat_id: UUID,
) -> SmartAppEvent:
    return SmartAppEvent(
        bot=BotAccount(
            id=bot_account.id,
            host=bot_account.host,
        ),
        ref=uuid4(),
        smartapp_id=bot_account.id,
        data={"method": method_name, "params": payload, "type": "smartapp_rpc"},
        opts={},
        smartapp_api_version=1,
        files=[],
        sender=UserSender(
            huid=user_info.huid,
            udid=user_udid,
            ad_login=user_info.ad_login,
            ad_domain=user_info.ad_domain,
            username=user_info.username,
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


class RPCAuth(APIKeyHeader):
    PATTERN = "([^?=&]+)=([^&]*)"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    async def __call__(self, request: Request) -> RPCAuthConfig:  # type: ignore
        api_key = request.headers.get(self.model.name)
        if not api_key:
            return RPCAuthConfig()

        result = re.findall(self.PATTERN, api_key)
        if not result:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Invalid RPC Auth format"
            )
        try:
            config = RPCAuthConfig(**dict(result))
        except ValidationError as ex:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=str(ex))

        return config


security = RPCAuth(
    scheme_name="RPC Auth",
    name="X-RPC-AUTH",
    description="""
    
    Format: `bot_id=282bd294-c60a-5343-91a0-12dd0d23c03c&sender_huid=282bd294-c60a-5343-91a0-12dd0d23c03c&sender_udid=282bd294-c60a-5343-91a0-12dd0d23c03c&chat_id=282bd294-c60a-5343-91a0-12dd0d23c03c`
    """,
)
