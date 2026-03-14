import logging

from aiogram import Router, types
from aiogram.filters import Command

from ..texts import welcome_text, welcome_markup, help_text

logger = logging.getLogger('steam_showcase_bot.handlers.commands')

router = Router(name='commands')


@router.message(Command('start'))
async def cmd_start(message: types.Message):
    logger.info('cmd_start: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    first_name = getattr(getattr(message, 'from_user', None), 'first_name', None) or 'друг'
    await message.answer(
        welcome_text(first_name),
        parse_mode='HTML',
        reply_markup=welcome_markup(),
    )


@router.message(Command('help'))
async def cmd_help(message: types.Message):
    logger.info('cmd_help: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    await message.answer(help_text(), parse_mode='HTML')
