import logging

from aiogram import Bot, Dispatcher, F, Router, types

from ..i18n import get_user_locale, locale_display_name, set_user_locale, tr
from ..texts import about_showcase_text, help_text, language_markup, welcome_markup

logger = logging.getLogger('steam_showcase_bot.handlers.callbacks')

router = Router(name='callbacks')


@router.callback_query(F.data.in_({'help', 'about_showcase'}))
async def handle_callback(callback: types.CallbackQuery, bot: Bot, dispatcher: Dispatcher):
    """Обрабатывает нажатия на инлайн-кнопки."""
    data = callback.data
    user = getattr(callback, 'from_user', None)
    locale = await get_user_locale(
        dispatcher,
        bot,
        getattr(user, 'id', None),
        getattr(user, 'language_code', None),
    )
    try:
        if data == 'help':
            await callback.message.answer(help_text(locale), parse_mode='HTML')
        elif data == 'about_showcase':
            await callback.message.answer(about_showcase_text(locale), parse_mode='HTML')
        await callback.answer()
    except Exception:
        logger.exception('handle_callback error: data=%s', data)
        try:
            await callback.answer(tr('callback_error', locale))
        except Exception:
            pass


@router.callback_query(F.data == 'choose_language')
async def handle_choose_language(callback: types.CallbackQuery, bot: Bot, dispatcher: Dispatcher):
    user = getattr(callback, 'from_user', None)
    locale = await get_user_locale(
        dispatcher,
        bot,
        getattr(user, 'id', None),
        getattr(user, 'language_code', None),
    )
    try:
        if callback.message is not None:
            await callback.message.answer(
                tr('language_choose_title', locale),
                parse_mode='HTML',
                reply_markup=language_markup(locale),
            )
        await callback.answer()
    except Exception:
        logger.exception('handle_choose_language error')
        try:
            await callback.answer(tr('callback_error', locale))
        except Exception:
            pass


@router.callback_query(F.data.startswith('set_lang:'))
async def handle_set_language(callback: types.CallbackQuery, bot: Bot, dispatcher: Dispatcher):
    user = getattr(callback, 'from_user', None)
    user_id = getattr(user, 'id', None)
    tg_locale = getattr(user, 'language_code', None)
    selected = (callback.data or '').split(':', 1)[1]
    locale = await set_user_locale(dispatcher, bot, user_id, selected)
    try:
        if callback.message is not None:
            await callback.message.answer(
                tr(
                    'language_changed',
                    locale,
                    language_name=locale_display_name(locale, locale),
                ),
                parse_mode='HTML',
                reply_markup=welcome_markup(locale),
            )
        await callback.answer(tr('language_changed_short', locale))
    except Exception:
        logger.exception('handle_set_language error: selected=%s', selected)
        fallback_locale = await get_user_locale(dispatcher, bot, user_id, tg_locale)
        try:
            await callback.answer(tr('callback_error', fallback_locale))
        except Exception:
            pass
