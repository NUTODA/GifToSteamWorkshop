import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from .config import (
    FFMPEG_TERMINATE_TIMEOUT,
    FSM_STORAGE,
    HEARTBEAT_FILE,
    HEARTBEAT_INTERVAL_SECONDS,
    LOG_FILE,
    LOG_LEVEL,
    LOG_TO_FILE,
    MAX_CONCURRENT_TASKS,
    RATE_LIMIT_SECONDS,
    REDIS_URL,
    SHUTDOWN_TASK_WAIT_TIMEOUT,
    TELEGRAM_CLIENT_CONNECT_LIMIT,
    TELEGRAM_CLIENT_TIMEOUT,
)
from .config import (
    TELEGRAM_BOT_TOKEN as TOKEN,
)
from .ffmpeg_utils import terminate_running_ffmpeg_processes
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


def _build_fsm_storage():
    if FSM_STORAGE == 'redis':
        if not REDIS_URL:
            logger.warning('FSM_STORAGE=redis, но REDIS_URL пуст. Использую MemoryStorage.')
            return MemoryStorage()
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            logger.info('FSM storage: RedisStorage')
            return RedisStorage.from_url(REDIS_URL)
        except Exception:
            logger.exception('Не удалось инициализировать RedisStorage. Использую MemoryStorage.')
            return MemoryStorage()

    if FSM_STORAGE != 'memory':
        logger.warning('Неизвестное значение FSM_STORAGE=%s. Использую MemoryStorage.', FSM_STORAGE)

    logger.info('FSM storage: MemoryStorage')
    return MemoryStorage()


dp = Dispatcher(storage=_build_fsm_storage())

_custom_session: AiohttpSession | None = None


async def _heartbeat_writer(stop_event: asyncio.Event) -> None:
    """Периодически обновляет heartbeat-файл для Docker healthcheck."""
    heartbeat_path = Path(HEARTBEAT_FILE)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)

    while not stop_event.is_set():
        heartbeat_path.write_text(str(int(asyncio.get_running_loop().time())), encoding='utf-8')
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


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
    dp['is_stopping'] = False
    dp['active_processing_tasks'] = set()
    stop_event = asyncio.Event()
    dp['heartbeat_stop_event'] = stop_event
    dp['heartbeat_task'] = asyncio.create_task(_heartbeat_writer(stop_event))
    logger.info('ProcessingService ready (max_concurrent=%d)', MAX_CONCURRENT_TASKS)


async def on_shutdown() -> None:
    """Корректно останавливает фоновые задачи и закрывает сессию."""
    global _custom_session
    dp['is_stopping'] = True

    active_tasks = dp.workflow_data.get('active_processing_tasks')
    if isinstance(active_tasks, set) and active_tasks:
        logger.info('Waiting for %d active processing tasks', len(active_tasks))
        done, pending = await asyncio.wait(active_tasks, timeout=SHUTDOWN_TASK_WAIT_TIMEOUT)
        if pending:
            logger.warning('Cancelling %d hanging processing tasks', len(pending))
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        logger.info('Processing tasks completed: %d, cancelled: %d', len(done), len(pending))

    terminated, killed = terminate_running_ffmpeg_processes(FFMPEG_TERMINATE_TIMEOUT)
    if terminated:
        logger.info('Stopped ffmpeg processes: terminated=%d, killed=%d', terminated, killed)

    heartbeat_stop_event = dp.workflow_data.get('heartbeat_stop_event')
    heartbeat_task = dp.workflow_data.get('heartbeat_task')
    if isinstance(heartbeat_stop_event, asyncio.Event):
        heartbeat_stop_event.set()
    if isinstance(heartbeat_task, asyncio.Task):
        try:
            await heartbeat_task
        except Exception:
            logger.exception('Error while stopping heartbeat task')

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
