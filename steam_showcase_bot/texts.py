import html as _html_module

from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import MAX_ARCHIVE_SEND_MB
from .i18n import locale_display_name, normalize_locale, tr

STEP_SCALE = 1
STEP_SLICE = 2
STEP_GIFS = 3
STEP_ZIP = 4
STEP_DONE = 5


def esc(text: str) -> str:
    """Экранирует HTML-символы для Telegram HTML parse_mode."""
    return _html_module.escape(str(text))


def welcome_markup(locale: str) -> InlineKeyboardMarkup:
    ui_locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=tr('button_help', ui_locale), callback_data='help')
    builder.button(text=tr('button_about_showcase', ui_locale), callback_data='about_showcase')
    builder.button(text=tr('button_language', ui_locale), callback_data='choose_language')
    builder.adjust(2, 1)
    return builder.as_markup()


def language_markup(locale: str) -> InlineKeyboardMarkup:
    ui_locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    for lang in ('ru', 'en', 'uk'):
        title = locale_display_name(lang, ui_locale)
        if lang == ui_locale:
            title = f'✅ {title}'
        builder.button(text=title, callback_data=f'set_lang:{lang}')
    builder.adjust(3)
    return builder.as_markup()


def welcome_text(first_name: str, locale: str) -> str:
    return tr('welcome_text', locale, first_name=esc(first_name))


def help_text(locale: str) -> str:
    return tr('help_text', locale, limit_mb=esc(MAX_ARCHIVE_SEND_MB))


def about_showcase_text(locale: str) -> str:
    return tr('about_showcase_text', locale)


def status_text(
    filename: str,
    size_mb: float | None = None,
    step: int = 0,
    failed_at: int | None = None,
    error_msg: str | None = None,
    locale: str = 'ru',
) -> str:
    """Формирует HTML-текст прогресс-статуса обработки файла."""
    size_str = f' <i>({size_mb:.1f} MB)</i>' if size_mb is not None else ''

    step_defs = [
        (STEP_SCALE, tr('status_step_scale', locale)),
        (STEP_SLICE, tr('status_step_slice', locale)),
        (STEP_GIFS, tr('status_step_gifs', locale)),
        (STEP_ZIP, tr('status_step_zip', locale)),
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
        header = tr('status_header_failed', locale, err_detail=err_detail)
    elif step >= STEP_DONE:
        header = tr('status_header_done', locale)
    elif step == 0:
        header = tr('status_header_start', locale)
    else:
        header = tr('status_header_progress', locale)

    return tr(
        'status_file_received',
        locale,
        filename=esc(filename),
        size_str=size_str,
        header=header,
        steps_block=steps_block,
    )


async def edit_status(msg: types.Message | None, **kwargs) -> None:
    """Тихо редактирует статус-сообщение, игнорируя ошибки."""
    if msg is None:
        return
    try:
        await msg.edit_text(status_text(**kwargs), parse_mode='HTML')
    except Exception:
        pass
