from aiogram import Dispatcher

from .callbacks import router as callbacks_router
from .commands import router as commands_router
from .media import router as media_router


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)
    dp.include_router(media_router)
