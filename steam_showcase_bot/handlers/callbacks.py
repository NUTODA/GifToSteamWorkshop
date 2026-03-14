import logging

from aiogram import Router, types, F

from ..texts import help_text, about_showcase_text

logger = logging.getLogger('steam_showcase_bot.handlers.callbacks')

router = Router(name='callbacks')


@router.callback_query(F.data.in_({'help', 'about_showcase'}))
async def handle_callback(callback: types.CallbackQuery):
    """Обрабатывает нажатия на инлайн-кнопки."""
    data = callback.data
    try:
        if data == 'help':
            await callback.message.answer(help_text(), parse_mode='HTML')
        elif data == 'about_showcase':
            await callback.message.answer(about_showcase_text(), parse_mode='HTML')
        await callback.answer()
    except Exception:
        logger.exception('handle_callback error: data=%s', data)
        try:
            await callback.answer('Ошибка при обработке кнопки.')
        except Exception:
            pass
