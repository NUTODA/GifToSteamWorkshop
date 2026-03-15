import logging

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command

from ..i18n import get_user_locale, set_user_locale, tr
from ..texts import help_text, language_markup, welcome_markup, welcome_text

logger = logging.getLogger('steam_showcase_bot.handlers.commands')

router = Router(name='commands')


@router.message(Command('start'))
async def cmd_start(message: types.Message, bot: Bot, dispatcher: Dispatcher):
    logger.info('cmd_start: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    user = getattr(message, 'from_user', None)
    user_id = getattr(user, 'id', None)
    tg_locale = getattr(user, 'language_code', None)
    locale = await get_user_locale(dispatcher, bot, user_id, tg_locale)
    locale = await set_user_locale(dispatcher, bot, user_id, locale)
    first_name = getattr(getattr(message, 'from_user', None), 'first_name', None) or 'друг'
    await message.answer(
        welcome_text(first_name, locale),
        parse_mode='HTML',
        reply_markup=welcome_markup(locale),
    )


@router.message(Command('help'))
async def cmd_help(message: types.Message, bot: Bot, dispatcher: Dispatcher):
    logger.info('cmd_help: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    user = getattr(message, 'from_user', None)
    locale = await get_user_locale(
        dispatcher,
        bot,
        getattr(user, 'id', None),
        getattr(user, 'language_code', None),
    )
    await message.answer(help_text(locale), parse_mode='HTML')


@router.message(Command('lang'))
@router.message(Command('language'))
async def cmd_lang(message: types.Message, bot: Bot, dispatcher: Dispatcher):
    logger.info('cmd_lang: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    user = getattr(message, 'from_user', None)
    locale = await get_user_locale(
        dispatcher,
        bot,
        getattr(user, 'id', None),
        getattr(user, 'language_code', None),
    )
    await message.answer(
        tr('language_choose_title', locale),
        parse_mode='HTML',
        reply_markup=language_markup(locale),
    )
