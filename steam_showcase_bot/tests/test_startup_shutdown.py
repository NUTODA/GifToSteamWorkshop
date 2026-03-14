import asyncio
import sys

import steam_showcase_bot.bot as botmod


def test_import_does_not_crash():
    """Импорт модуля не должен вызывать RuntimeError 'no running event loop'."""
    assert hasattr(botmod, 'bot')
    assert hasattr(botmod, 'dp')


def test_on_startup_creates_session():
    """on_startup создаёт кастомную aiohttp-сессию и ProcessingService."""
    if 'aiohttp' not in sys.modules:
        try:
            import aiohttp  # noqa: F401
        except Exception:
            return

    asyncio.run(botmod.on_startup())

    assert botmod._custom_session is not None
    assert 'processor' in botmod.dp.workflow_data

    asyncio.run(botmod.on_shutdown())
    assert botmod._custom_session is None


def test_on_shutdown_is_safe_without_startup():
    """on_shutdown не падает, если on_startup не вызывался."""
    botmod._custom_session = None
    asyncio.run(botmod.on_shutdown())
    assert botmod._custom_session is None
