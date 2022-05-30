"""Configuration for bot instance."""
from typing import Optional

from httpx import AsyncClient, Limits
from pybotx import Bot, CallbackRepoProto

from app.bot.commands import common
from app.settings import settings

BOTX_CALLBACK_TIMEOUT = 30


def get_bot(callback_repo: Optional[CallbackRepoProto] = None) -> Bot:
    return Bot(
        collectors=[common.collector],
        bot_accounts=settings.BOT_CREDENTIALS,
        default_callback_timeout=BOTX_CALLBACK_TIMEOUT,
        httpx_client=AsyncClient(
            timeout=60,
            limits=Limits(max_keepalive_connections=None, max_connections=None),
        ),
        callback_repo=callback_repo,
    )
