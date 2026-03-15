import asyncio

from steam_showcase_bot.i18n import (
    get_user_locale,
    normalize_locale,
    resolve_locale,
    set_user_locale,
    tr,
)


class _DummyState:
    def __init__(self):
        self._data = {}

    async def get_data(self):
        return dict(self._data)

    async def update_data(self, **kwargs):
        self._data.update(kwargs)


class _DummyFSM:
    def __init__(self):
        self._state = _DummyState()

    def get_context(self, bot, chat_id, user_id):
        return self._state


class _DummyDispatcher:
    def __init__(self):
        self.fsm = _DummyFSM()


def test_normalize_locale_supports_telegram_formats():
    assert normalize_locale('ru-RU') == 'ru'
    assert normalize_locale('en_US') == 'en'
    assert normalize_locale('uk') == 'uk'


def test_resolve_locale_falls_back_to_telegram_then_default():
    assert resolve_locale('zz', 'uk-UA') == 'uk'
    assert resolve_locale(None, 'fr') == 'ru'


def test_tr_falls_back_to_default_language():
    assert tr('button_help', 'fr') == '📖 Справка'


def test_user_locale_can_be_saved_and_loaded():
    dispatcher = _DummyDispatcher()
    bot = object()

    saved = asyncio.run(set_user_locale(dispatcher, bot, 123, 'en-US'))
    loaded = asyncio.run(get_user_locale(dispatcher, bot, 123, 'ru-RU'))

    assert saved == 'en'
    assert loaded == 'en'
