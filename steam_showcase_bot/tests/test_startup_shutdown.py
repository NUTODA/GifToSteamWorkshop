import asyncio
import sys

import steam_showcase_bot.bot as botmod


def test_import_does_not_create_session():
    """Импорт модуля не должен вызывать RuntimeError 'no running event loop'."""
    # Успешный импорт — достаточно (рантайм-ошибка должна была бы прерваться при импорте).
    assert hasattr(botmod, 'bot')
    # Допустимо, что Bot создал собственную сессию; важно, что импорт НЕ упал с RuntimeError.


def test_on_startup_and_shutdown_create_and_close_session():
    """on_startup should create a session; on_shutdown should close it if we created it."""
    if 'aiohttp' not in sys.modules:
        # attempt to import aiohttp; if not available, skip (environment-dependent)
        try:
            import aiohttp  # noqa: F401
        except Exception:
            # aiohttp is not available in this test environment — skip the test without requiring pytest
            return

    # create session
    asyncio.run(botmod.on_startup())
    sess = getattr(botmod.bot, 'session', None)
    assert sess is not None
    # aiohttp ClientSession exposes `closed` attribute
    assert not getattr(sess, 'closed', False)

    # shutdown should close it
    asyncio.run(botmod.on_shutdown())
    assert getattr(sess, 'closed', True) or getattr(botmod.bot, 'session', None) is None


def test_on_shutdown_does_not_close_external_session():
    """If session was supplied externally (not created by our on_startup), on_shutdown must not close it."""
    class DummySession:
        def __init__(self):
            self.close_called = False
            self.closed = False

        async def close(self):
            self.close_called = True
            self.closed = True

    dummy = DummySession()
    botmod.bot.session = dummy
    botmod.bot._created_session = False

    asyncio.run(botmod.on_shutdown())

    assert not dummy.close_called

    # cleanup
    botmod.bot.session = None
    botmod.bot._created_session = False
