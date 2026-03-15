import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from ..i18n import get_user_locale, resolve_locale, tr

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
                locale = resolve_locale(None, getattr(user, 'language_code', None))
                dispatcher = data.get('dispatcher')
                bot = data.get('bot')
                if dispatcher is not None and bot is not None:
                    locale = await get_user_locale(
                        dispatcher,
                        bot,
                        getattr(user, 'id', None),
                        getattr(user, 'language_code', None),
                    )
                await event.answer(
                    tr('throttling_wait', locale, remaining=remaining),
                    parse_mode='HTML',
                )
                return None
            self._user_timestamps[user.id] = now

        return await handler(event, data)
