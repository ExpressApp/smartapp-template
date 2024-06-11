"""Handlers for default bot commands and system events."""

from pybotx import (
    Bot,
    HandlerCollector,
    IncomingMessage,
    SmartAppEvent,
    SyncSmartAppRequestResponsePayload,
)

from app.smartapp.smartapp import smartapp

collector = HandlerCollector()


@collector.smartapp_event
async def handle_smartapp_event(event: SmartAppEvent, bot: Bot) -> None:
    await smartapp.handle_smartapp_event(event, bot)


@collector.sync_smartapp_request
async def handle_sync_smartapp_request(
    event: SmartAppEvent, bot: Bot
) -> SyncSmartAppRequestResponsePayload:
    return await smartapp.handle_sync_smartapp_request(event, bot)


@collector.command("/_test-redis-callback-repo", visible=False)
async def test_redis_callback_repo(message: IncomingMessage, bot: Bot) -> None:
    """Testing redis callback."""
    await bot.answer_message("Hello!", callback_timeout=0.5)


@collector.command("/_test-redis-callback-repo-wait", visible=False)
async def test_redis_callback_repo_wait(message: IncomingMessage, bot: Bot) -> None:
    """Testing redis wait callback."""
    sync_id = await bot.answer_message(
        "Hello!", callback_timeout=0.5, wait_callback=False
    )
    await bot.wait_botx_method_callback(sync_id)


@collector.command("/_test-redis-callback-repo-no-wait", visible=False)
async def test_redis_callback_repo_not_wait(message: IncomingMessage, bot: Bot) -> None:
    """Testing redis repo callback not wait."""
    await bot.answer_message("Hello!", callback_timeout=0, wait_callback=False)
