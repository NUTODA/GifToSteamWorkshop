import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from .config import (
    TELEGRAM_BOT_TOKEN as TOKEN,
    LOG_LEVEL, LOG_FILE, LOG_TO_FILE,
    TELEGRAM_CLIENT_TIMEOUT, TELEGRAM_CLIENT_CONNECT_LIMIT,
    RATE_LIMIT_SECONDS, MAX_CONCURRENT_TASKS, DEBUG_MODE,
)
from .handlers import register_routers
from .handlers.media import router as media_router
from .middlewares.throttling import ThrottlingMiddleware
from .services.processor import ProcessingService

logger = logging.getLogger('steam_showcase_bot')
numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
handlers = [logging.StreamHandler()]
if LOG_TO_FILE:
    try:
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        handlers.append(fh)
    except Exception:
        pass
logging.basicConfig(
    level=numeric_level,
    handlers=handlers,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)
logger.setLevel(numeric_level)

if not TOKEN:
    logger.warning('Please set TELEGRAM_BOT_TOKEN in .env or environment')

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher(storage=MemoryStorage())

_custom_session: AiohttpSession | None = None


async def on_startup() -> None:
    """Создаёт aiohttp-сессию и семафор внутри event loop."""
    global _custom_session

    if bot is None:
        return

    limit = TELEGRAM_CLIENT_CONNECT_LIMIT if TELEGRAM_CLIENT_CONNECT_LIMIT > 0 else 100
    session = AiohttpSession(
        timeout=float(TELEGRAM_CLIENT_TIMEOUT),
        limit=limit,
    )
    bot.session = session
    _custom_session = session
    logger.info(
        'Created aiohttp session (timeout=%s, connect_limit=%s)',
        TELEGRAM_CLIENT_TIMEOUT, limit,
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    processor = ProcessingService(bot=bot, semaphore=semaphore)
    dp['processor'] = processor
    logger.info('ProcessingService ready (max_concurrent=%d)', MAX_CONCURRENT_TASKS)


async def on_shutdown() -> None:
    """Закрывает aiohttp-сессию, если мы её создавали."""
    global _custom_session

    if _custom_session is not None:
        try:
            await _custom_session.close()
            logger.info('Closed custom aiohttp session')
        except Exception:
            logger.exception('Error closing aiohttp session')
        _custom_session = None


def _setup() -> None:
    """Регистрирует роутеры, middleware и lifecycle-хуки."""
    media_router.message.middleware(ThrottlingMiddleware(rate_limit=RATE_LIMIT_SECONDS))
    logger.info('ThrottlingMiddleware attached (rate_limit=%.1f s)', RATE_LIMIT_SECONDS)

    register_routers(dp)
    logger.info('Routers registered')

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)


_setup()


def main() -> None:
    if not TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN not set')

    async def _run():
        try:
            logger.info('Starting polling...')
            await dp.start_polling(bot)
        finally:
            if bot:
                await bot.session.close()

    asyncio.run(_run())


if __name__ == '__main__':
    main()
