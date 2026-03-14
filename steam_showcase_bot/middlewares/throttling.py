import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger('steam_showcase_bot.throttling')


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничивает частоту отправки медиафайлов одним пользователем."""

    def __init__(self, rate_limit: float = 30.0):
        self._rate_limit = rate_limit
        self._user_timestamps: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user = data.get('event_from_user')
        if user:
            now = asyncio.get_event_loop().time()
            last = self._user_timestamps.get(user.id, 0.0)
            if now - last < self._rate_limit:
                remaining = int(self._rate_limit - (now - last)) + 1
                logger.debug('Throttled user %s: %d sec remaining', user.id, remaining)
                await event.answer(
                    f'⏳ <b>Подожди немного</b>\n\n'
                    f'Следующий файл можно отправить через <code>{remaining}</code> сек.',
                    parse_mode='HTML',
                )
                return None
            self._user_timestamps[user.id] = now

        return await handler(event, data)
