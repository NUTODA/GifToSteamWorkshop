import html as _html_module
import os

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


STEP_SCALE = 1
STEP_SLICE = 2
STEP_GIFS = 3
STEP_ZIP = 4
STEP_DONE = 5


def esc(text: str) -> str:
    """Экранирует HTML-символы для Telegram HTML parse_mode."""
    return _html_module.escape(str(text))


def welcome_markup() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='📖 Справка', callback_data='help')
    builder.button(text='🎮 Что такое Витрина?', callback_data='about_showcase')
    builder.adjust(2)
    return builder.as_markup()


def welcome_text(first_name: str) -> str:
    return (
        f'🎬 <b>Steam Showcase Bot</b>\n\n'
        f'Привет, {esc(first_name)}! 👋\n\n'
        f'Я автоматически подготовлю твою анимацию для <b>Витрины Steam</b>.\n\n'
        f'<b>📌 Как это работает:</b>\n'
        f'Витрина отображает GIF через 5 горизонтальных слотов по <code>150 px</code>. Я:\n\n'
        f'1️⃣  Масштабирую видео до <code>750 px</code>\n'
        f'2️⃣  Нарезаю на <b>5 частей</b> по <code>150 px</code>\n'
        f'3️⃣  Конвертирую каждую часть в <code>.gif</code>\n'
        f'4️⃣  Упаковываю всё в <b>ZIP-архив</b>\n\n'
        f'🚀 <b>Просто отправь GIF или MP4-видео — остальное сделаю я!</b>'
    )


def help_text() -> str:
    limit_mb = os.getenv('MAX_ARCHIVE_SEND_MB', '50')
    return (
        f'❓ <b>Справка — Steam Showcase Bot</b>\n\n'
        f'<b>Поддерживаемые форматы:</b>\n'
        f'• GIF-анимация (Telegram конвертирует её в MP4 автоматически)\n'
        f'• MP4-видео\n'
        f'• Файлы <code>.gif</code>, <code>.mp4</code>, <code>.webm</code> как документ\n\n'
        f'<b>Как использовать:</b>\n'
        f'1. Отправь GIF или видео прямо в этот чат\n'
        f'2. Дождись обработки (обычно 10–60 сек)\n'
        f'3. Получи ZIP с 5 готовыми GIF-файлами\n'
        f'4. Загрузи <code>part1.gif</code>…<code>part5.gif</code>\n'
        f'   в слоты Витрины на странице своего профиля Steam\n\n'
        f'<b>Команды:</b>\n'
        f'/start — главное меню\n'
        f'/help — эта справка\n\n'
        f'<b>⚠️ Частые вопросы:</b>\n'
        f'• <i>«Неподдерживаемый формат»</i> — отправь файл как GIF-анимацию, '
        f'а не как документ\n'
        f'• <i>«Архив слишком большой»</i> — файл создан на сервере, но превысил '
        f'лимит отправки {esc(limit_mb)} MB\n'
        f'• <i>«FFmpeg не найден»</i> — обратитесь к администратору сервера'
    )


def about_showcase_text() -> str:
    return (
        f'🎮 <b>Витрина Steam (Steam Showcase)</b>\n\n'
        f'Витрина — раздел профиля Steam, где можно разместить анимированные GIF-картинки. '
        f'Она состоит из <b>5 горизонтальных слотов</b>, каждый шириной <code>150 px</code>.\n\n'
        f'Чтобы анимация выглядела как единое целое, нужно:\n'
        f'1. Взять видео шириной <code>750 px</code> (5 × 150 px)\n'
        f'2. Разрезать на 5 равных частей\n'
        f'3. Загрузить каждую часть в соответствующий слот\n\n'
        f'<b>Именно это я делаю автоматически!</b> 🎉\n\n'
        f'Управление Витриной:\n'
        f'<code>steamcommunity.com → Профиль → Редактировать → Витрина</code>'
    )


def status_text(
    filename: str,
    size_mb: float | None = None,
    step: int = 0,
    failed_at: int | None = None,
    error_msg: str | None = None,
) -> str:
    """Формирует HTML-текст прогресс-статуса обработки файла."""
    size_str = f' <i>({size_mb:.1f} MB)</i>' if size_mb is not None else ''

    step_defs = [
        (STEP_SCALE, 'Масштабирование до <code>750 px</code>'),
        (STEP_SLICE, 'Нарезка на 5 частей'),
        (STEP_GIFS,  'Создание GIF-файлов'),
        (STEP_ZIP,   'Архивирование в ZIP'),
    ]

    rows = []
    for s, label in step_defs:
        if failed_at == s:
            icon = '❌'
        elif s < step or step >= STEP_DONE:
            icon = '✅'
        elif s == step:
            icon = '🔄'
        else:
            icon = '▫️'
        rows.append(f'{icon} {label}')
    steps_block = '\n'.join(rows)

    if failed_at is not None:
        err_detail = f'\n<i>{esc(str(error_msg)[:200])}</i>' if error_msg else ''
        header = f'❌ <b>Ошибка при обработке</b>{err_detail}'
    elif step >= STEP_DONE:
        header = '✅ <b>Готово! Отправляю архив…</b>'
    elif step == 0:
        header = '⏳ <b>Начинаю обработку…</b>'
    else:
        header = '⏳ <b>Идёт обработка…</b>'

    return (
        f'📥 <b>Файл получен:</b> <code>{esc(filename)}</code>{size_str}\n\n'
        f'{header}\n\n'
        f'{steps_block}'
    )


async def edit_status(msg: types.Message | None, **kwargs) -> None:
    """Тихо редактирует статус-сообщение, игнорируя ошибки."""
    if msg is None:
        return
    try:
        await msg.edit_text(status_text(**kwargs), parse_mode='HTML')
    except Exception:
        pass
