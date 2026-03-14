import os
import asyncio
import html as _html_module
from pathlib import Path
import logging
import shutil

from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramNetworkError
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .config import TELEGRAM_BOT_TOKEN as TOKEN, LOG_LEVEL, LOG_FILE, LOG_TO_FILE, SAVE_UPLOADS

# configure logging early so logs are available during import-time checks
logger = logging.getLogger('steam_showcase_bot')
numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
handlers = [logging.StreamHandler()]
if LOG_TO_FILE:
    try:
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        handlers.append(fh)
    except Exception:
        pass
logging.basicConfig(level=numeric_level, handlers=handlers, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
logger.setLevel(numeric_level)
logger.debug('Logger initialized: level=%s file=%s', LOG_LEVEL, LOG_FILE if LOG_TO_FILE else None)

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except Exception:
    VideoFileClip = None  # type: ignore
    MOVIEPY_AVAILABLE = False

# ffmpeg helper (resizer & slicer)
try:
    from .ffmpeg_utils import prepare_and_resize_copy, is_ffmpeg_available, slice_video_inplace_with_gifs
    FFMPEG_UTILS_AVAILABLE = True
except Exception:
    prepare_and_resize_copy = None
    is_ffmpeg_available = lambda: False  # type: ignore
    slice_video_inplace_with_gifs = None
    FFMPEG_UTILS_AVAILABLE = False


if not TOKEN:
    logger.warning('Please set TELEGRAM_BOT_TOKEN in .env or environment')

TELEGRAM_CLIENT_TIMEOUT = int(os.getenv('TELEGRAM_CLIENT_TIMEOUT', '300'))
TELEGRAM_CLIENT_CONNECT_LIMIT = int(os.getenv('TELEGRAM_CLIENT_CONNECT_LIMIT', '0'))
session = None
bot = None
if TOKEN:
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=TELEGRAM_CLIENT_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=TELEGRAM_CLIENT_CONNECT_LIMIT)
        session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        bot = Bot(token=TOKEN, session=session)
    except Exception:
        logger.exception('Failed to create aiohttp session for Bot; falling back to default')
        bot = Bot(token=TOKEN)
else:
    bot = None
dp = Dispatcher(storage=MemoryStorage())
DEBUG_MODE = (LOG_LEVEL or '').upper() == 'DEBUG' or os.getenv('BOT_DEBUG', '') == '1'
MAX_ARCHIVE_SEND_MB = int(os.getenv('MAX_ARCHIVE_SEND_MB', '50'))


# ─── Прогресс-шаги обработки ─────────────────────────────────────────────────

_STEP_SCALE   = 1   # масштабирование до 750px
_STEP_SLICE   = 2   # нарезка на части
_STEP_GIFS    = 3   # конвертация в GIF
_STEP_ZIP     = 4   # архивирование
_STEP_DONE    = 5   # всё готово


# ─── UI-хелперы ───────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Экранирует HTML-символы для Telegram HTML parse_mode."""
    return _html_module.escape(str(text))


def _welcome_markup() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='📖 Справка', callback_data='help')
    builder.button(text='🎮 Что такое Витрина?', callback_data='about_showcase')
    builder.adjust(2)
    return builder.as_markup()


def _welcome_text(first_name: str) -> str:
    return (
        f'🎬 <b>Steam Showcase Bot</b>\n\n'
        f'Привет, {_esc(first_name)}! 👋\n\n'
        f'Я автоматически подготовлю твою анимацию для <b>Витрины Steam</b>.\n\n'
        f'<b>📌 Как это работает:</b>\n'
        f'Витрина отображает GIF через 5 горизонтальных слотов по <code>150 px</code>. Я:\n\n'
        f'1️⃣  Масштабирую видео до <code>750 px</code>\n'
        f'2️⃣  Нарезаю на <b>5 частей</b> по <code>150 px</code>\n'
        f'3️⃣  Конвертирую каждую часть в <code>.gif</code>\n'
        f'4️⃣  Упаковываю всё в <b>ZIP-архив</b>\n\n'
        f'🚀 <b>Просто отправь GIF или MP4-видео — остальное сделаю я!</b>'
    )


def _help_text() -> str:
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
        f'лимит отправки {_esc(limit_mb)} MB\n'
        f'• <i>«FFmpeg не найден»</i> — обратитесь к администратору сервера'
    )


def _about_showcase_text() -> str:
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


def _status_text(
    filename: str,
    size_mb: float | None = None,
    step: int = 0,
    failed_at: int | None = None,
    error_msg: str | None = None,
) -> str:
    """Формирует HTML-текст прогресс-статуса обработки файла."""
    size_str = f' <i>({size_mb:.1f} MB)</i>' if size_mb is not None else ''

    step_defs = [
        (_STEP_SCALE, 'Масштабирование до <code>750 px</code>'),
        (_STEP_SLICE, 'Нарезка на 5 частей'),
        (_STEP_GIFS,  'Создание GIF-файлов'),
        (_STEP_ZIP,   'Архивирование в ZIP'),
    ]

    rows = []
    for s, label in step_defs:
        if failed_at == s:
            icon = '❌'
        elif s < step or step >= _STEP_DONE:
            icon = '✅'
        elif s == step:
            icon = '🔄'
        else:
            icon = '▫️'
        rows.append(f'{icon} {label}')
    steps_block = '\n'.join(rows)

    if failed_at is not None:
        err_detail = f'\n<i>{_esc(str(error_msg)[:200])}</i>' if error_msg else ''
        header = f'❌ <b>Ошибка при обработке</b>{err_detail}'
    elif step >= _STEP_DONE:
        header = '✅ <b>Готово! Отправляю архив…</b>'
    elif step == 0:
        header = '⏳ <b>Начинаю обработку…</b>'
    else:
        header = '⏳ <b>Идёт обработка…</b>'

    return (
        f'📥 <b>Файл получен:</b> <code>{_esc(filename)}</code>{size_str}\n\n'
        f'{header}\n\n'
        f'{steps_block}'
    )


async def _edit_status(msg: types.Message | None, **kwargs) -> None:
    """Тихо редактирует статус-сообщение, игнорируя ошибки."""
    if msg is None:
        return
    try:
        await msg.edit_text(_status_text(**kwargs), parse_mode='HTML')
    except Exception:
        pass


# ─── Хендлеры команд ─────────────────────────────────────────────────────────

async def cmd_start(message: types.Message):
    logger.info('cmd_start: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    first_name = getattr(getattr(message, 'from_user', None), 'first_name', None) or 'друг'
    await message.answer(
        _welcome_text(first_name),
        parse_mode='HTML',
        reply_markup=_welcome_markup(),
    )


async def cmd_help(message: types.Message):
    logger.info('cmd_help: from=%s', getattr(getattr(message, 'from_user', None), 'id', None))
    await message.answer(_help_text(), parse_mode='HTML')


async def handle_callback(callback: types.CallbackQuery):
    """Обрабатывает нажатия на инлайн-кнопки."""
    data = callback.data
    try:
        if data == 'help':
            await callback.message.answer(_help_text(), parse_mode='HTML')
        elif data == 'about_showcase':
            await callback.message.answer(_about_showcase_text(), parse_mode='HTML')
        await callback.answer()
    except Exception:
        logger.exception('handle_callback error: data=%s', data)
        try:
            await callback.answer('Ошибка при обработке кнопки.')
        except Exception:
            pass


# ─── Сохранение файла ────────────────────────────────────────────────────────

def _save_to_gifs(src_path: Path, message: types.Message, gifs_dir: Path, orig_name: str | None = None) -> Path:
    """Copy the uploaded gif (src_path) into gifs_dir with a unique name and return the dest path."""
    try:
        gifs_dir.mkdir(exist_ok=True)
    except Exception:
        pass
    import datetime
    user_id = getattr(message.from_user, 'id', 'unknown')
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    name = orig_name or src_path.name
    if not Path(name).suffix:
        name = f'{name}.gif'
    dest = gifs_dir / f'{user_id}_{ts}_{name}'
    try:
        shutil.copy2(src_path, dest)
        logger.info('Saved uploaded GIF to %s', dest)
        return dest
    except Exception:
        logger.exception('Ошибка при сохранении gif')
        return dest


# ─── Основной хендлер медиафайлов ────────────────────────────────────────────

async def handle_file(message: types.Message):
    """Скачивает GIF/видео, создаёт прогресс-сообщение и запускает обработку."""
    import datetime

    gifs_dir = Path(__file__).parent / 'gifs'
    gifs_dir.mkdir(exist_ok=True)

    user_id = getattr(message.from_user, 'id', 'unknown')
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    anim = getattr(message, 'animation', None)
    doc  = message.document
    vid  = getattr(message, 'video', None)

    anim_name  = getattr(anim, 'file_name', None)  if anim else None
    doc_name   = getattr(doc,  'file_name', None)  if doc  else None
    doc_mime   = getattr(doc,  'mime_type', None)  if doc  else None
    video_name = getattr(vid,  'file_name', None)  if vid  else None

    logger.info(
        'handle_file: msg_id=%s from=%s anim=%s doc=%s video=%s anim_name=%s doc_name=%s doc_mime=%s',
        message.message_id, user_id,
        bool(anim), bool(doc), bool(vid),
        anim_name, doc_name, doc_mime,
    )

    async def download_file(file_obj, dest_path: Path):
        file_id = file_obj.file_id
        logger.debug('Downloading file_id=%s to %s', file_id, dest_path)
        await bot.download(file_id, destination=dest_path)
        logger.info('Downloaded to %s (%d bytes)', dest_path, dest_path.stat().st_size)
        return dest_path

    async def _maybe_start_prepare_task(src_path: Path, visible_name: str, status_msg: types.Message | None = None):
        """Фоновая задача: resize → slice → GIF → ZIP → отправка."""
        _sz: float | None = None
        try:
            _sz = src_path.stat().st_size / (1024 * 1024)
        except Exception:
            pass

        async def _upd(step: int, failed_at: int | None = None, error_msg: str | None = None):
            await _edit_status(status_msg, filename=visible_name, size_mb=_sz,
                               step=step, failed_at=failed_at, error_msg=error_msg)

        if not FFMPEG_UTILS_AVAILABLE:
            logger.debug('FFmpeg utils not available; skipping prepare task')
            return

        try:
            if not is_ffmpeg_available():
                logger.warning('ffmpeg executable not found; skipping prepare task')
                await _upd(0, failed_at=_STEP_SCALE, error_msg='FFmpeg не найден на сервере')
                try:
                    if src_path.exists():
                        src_path.unlink()
                        logger.info('Removed upload %s because ffmpeg is unavailable', src_path)
                except Exception:
                    logger.exception('Failed to remove upload %s when ffmpeg missing', src_path)
                try:
                    await message.answer(
                        '⚠️ <b>FFmpeg не найден</b>\n\n'
                        'Обработка невозможна. Попросите администратора установить '
                        '<code>ffmpeg</code> и добавить его в PATH или задать '
                        'переменную окружения <code>FFMPEG_BIN</code>.',
                        parse_mode='HTML',
                    )
                except Exception:
                    pass
                return
        except Exception:
            logger.exception('Error checking ffmpeg availability')
            try:
                if src_path.exists():
                    src_path.unlink()
            except Exception:
                pass
            return

        if src_path.suffix.lower() != '.mp4':
            logger.debug('Source not mp4, skipping prepare task: %s', src_path)
            await _upd(0, failed_at=_STEP_SCALE, error_msg='Неподдерживаемый формат файла')
            try:
                if src_path.exists():
                    src_path.unlink()
                    logger.info('Removed non-mp4 upload %s', src_path)
            except Exception:
                logger.exception('Failed to remove non-mp4 upload %s', src_path)
            try:
                await message.answer(
                    '⚠️ <b>Неподдерживаемый формат</b>\n\n'
                    f'Получен файл <code>{_esc(visible_name)}</code>.\n\n'
                    'Бот принимает только <b>MP4-файлы</b>. Telegram автоматически '
                    'конвертирует GIF-анимации в MP4 — попробуй отправить файл '
                    'как GIF-анимацию, а не как документ.',
                    parse_mode='HTML',
                )
            except Exception:
                pass
            return

        prepared_dir = Path(__file__).parent / 'prepared_gifs'
        loop = asyncio.get_running_loop()

        try:
            assert prepare_and_resize_copy is not None
            await _upd(_STEP_SCALE)
            prepared = await loop.run_in_executor(None, prepare_and_resize_copy, src_path, prepared_dir)

            sliced_dir = Path(__file__).parent / 'sliced_gifs'
            sliced_dir.mkdir(exist_ok=True)
            sliced_copy = sliced_dir / prepared.name
            shutil.copy2(prepared, sliced_copy)
            logger.info('Copied prepared file to %s for slicing', sliced_copy)

            if slice_video_inplace_with_gifs:
                await _upd(_STEP_SLICE)
                try:
                    archive_path = await loop.run_in_executor(None, slice_video_inplace_with_gifs, sliced_copy)
                except Exception as e:
                    logger.exception('Ошибка при нарезке файла %s', sliced_copy)
                    await _upd(0, failed_at=_STEP_GIFS, error_msg=str(e))
                    for path in (sliced_copy, prepared, src_path):
                        try:
                            if path.exists():
                                path.unlink()
                                logger.info('Removed %s after failed slicing', path)
                        except Exception:
                            logger.exception('Failed to remove %s', path)
                    try:
                        for f in sliced_dir.glob(f'{sliced_copy.stem}*'):
                            try:
                                if f.is_dir():
                                    shutil.rmtree(f)
                                else:
                                    f.unlink()
                                logger.info('Removed artifact %s', f)
                            except Exception:
                                logger.exception('Failed to remove artifact %s', f)
                    except Exception:
                        logger.exception('Error while cleaning artifacts in %s', sliced_dir)
                    try:
                        await message.answer(
                            f'❌ <b>Ошибка при создании GIF:</b>\n'
                            f'<code>{_esc(str(e)[:300])}</code>',
                            parse_mode='HTML',
                        )
                    except Exception:
                        pass
                    return

                # Удаляем промежуточные файлы после успешной обработки
                for path in (src_path, prepared):
                    try:
                        if path.exists():
                            path.unlink()
                            logger.info('Removed intermediate file %s', path)
                    except Exception:
                        logger.exception('Failed to remove %s', path)

                try:
                    removed = []
                    for mp4 in sliced_dir.glob(f'{sliced_copy.stem}*.mp4'):
                        try:
                            mp4.unlink()
                            removed.append(mp4.name)
                        except Exception:
                            logger.exception('Failed to remove intermediate mp4 %s', mp4)
                    if removed:
                        logger.info('Removed intermediate mp4 files: %s', ', '.join(removed))
                except Exception:
                    logger.exception('Error while cleaning .mp4 files in %s', sliced_dir)

                # Отправляем архив пользователю
                await _upd(_STEP_DONE)
                try:
                    if archive_path:
                        archive = Path(archive_path)
                        if archive.exists():
                            size_mb = archive.stat().st_size / (1024 * 1024)
                            if size_mb > MAX_ARCHIVE_SEND_MB:
                                logger.warning(
                                    'Archive %s is too large (%.1f MB), limit %d MB',
                                    archive, size_mb, MAX_ARCHIVE_SEND_MB,
                                )
                                try:
                                    await message.answer(
                                        f'📦 <b>Архив готов, но слишком большой для отправки</b>\n\n'
                                        f'Размер: <code>{size_mb:.1f} MB</code> '
                                        f'(лимит: <code>{MAX_ARCHIVE_SEND_MB} MB</code>)\n\n'
                                        f'Архив сохранён на сервере и доступен администратору.',
                                        parse_mode='HTML',
                                    )
                                except Exception:
                                    pass
                            else:
                                send_attempts = int(os.getenv('ZIP_SEND_RETRIES', '3'))
                                send_timeout  = int(os.getenv('ZIP_SEND_TIMEOUT', '300'))
                                sent = False
                                for attempt in range(1, send_attempts + 1):
                                    try:
                                        fsfile  = FSInputFile(str(archive))
                                        caption = (
                                            f'🎬 <b>Архив готов!</b>\n\n'
                                            f'📦 Размер: <code>{size_mb:.1f} MB</code>\n'
                                            f'🗂 Файлов: <code>5 GIF</code> '
                                            f'(<code>part1.gif</code>…<code>part5.gif</code>)\n\n'
                                            f'<b>📋 Как загрузить в Steam:</b>\n'
                                            f'Профиль → Редактировать профиль → Витрина\n'
                                            f'→ Выбери слот → Загрузи каждый <code>partN.gif</code>'
                                        )
                                        await message.answer_document(
                                            document=fsfile,
                                            caption=caption,
                                            parse_mode='HTML',
                                            request_timeout=send_timeout,
                                        )
                                        logger.info(
                                            'Sent ZIP %s to user %s (size=%.1f MB) on attempt %d',
                                            archive, user_id, size_mb, attempt,
                                        )
                                        sent = True
                                        break
                                    except TelegramNetworkError as e:
                                        logger.warning(
                                            'Attempt %d: TelegramNetworkError sending %s: %s',
                                            attempt, archive, e,
                                        )
                                        if attempt < send_attempts:
                                            await asyncio.sleep(2 ** attempt)
                                        else:
                                            logger.exception(
                                                'Failed to send ZIP %s after %d attempts',
                                                archive, send_attempts,
                                            )
                                            try:
                                                await message.answer(
                                                    '⚠️ <b>Не удалось отправить архив</b>\n\n'
                                                    'Превышено число попыток из-за сетевых ошибок. '
                                                    'Архив сохранён на сервере.',
                                                    parse_mode='HTML',
                                                )
                                            except Exception:
                                                pass
                                    except Exception:
                                        logger.exception('Failed to send ZIP %s', archive)
                                        try:
                                            await message.answer(
                                                '⚠️ <b>Не удалось отправить архив</b>\n\n'
                                                'Произошла ошибка при отправке. '
                                                'Архив сохранён на сервере.',
                                                parse_mode='HTML',
                                            )
                                        except Exception:
                                            pass
                                        break
                                if not sent:
                                    logger.warning('Archive %s was not delivered to user %s', archive, user_id)
                        else:
                            logger.warning('Archive path returned but file missing: %s', archive_path)
                except Exception:
                    logger.exception('Unexpected error while sending archive')
                    try:
                        await message.answer(
                            '⚠️ <b>Ошибка при отправке архива</b>\n\nПроверьте логи сервера.',
                            parse_mode='HTML',
                        )
                    except Exception:
                        pass
            else:
                logger.debug('slice_video_inplace_with_gifs not available; skipping slicing')

        except Exception as e:
            logger.exception('Ошибка подготовки файла %s', src_path)
            await _upd(0, failed_at=_STEP_SCALE, error_msg=str(e))
            for path in (prepared_dir / src_path.name, src_path):
                try:
                    if path.exists():
                        path.unlink()
                        logger.info('Removed %s after preparation error', path)
                except Exception:
                    logger.exception('Failed to remove %s', path)
            try:
                await message.answer(
                    f'❌ <b>Ошибка при масштабировании:</b>\n'
                    f'<code>{_esc(str(e)[:300])}</code>',
                    parse_mode='HTML',
                )
            except Exception:
                pass

    try:
        if anim:
            fname = anim.file_name or 'animation.mp4'
            dest  = gifs_dir / f'{user_id}_{ts}_{fname}'
            status_msg = await message.answer('⬇️ <b>Скачиваю файл…</b>', parse_mode='HTML')
            await download_file(anim, dest)
            _sz = dest.stat().st_size / (1024 * 1024) if dest.exists() else None
            await _edit_status(status_msg, filename=fname, size_mb=_sz, step=0)
            asyncio.create_task(_maybe_start_prepare_task(dest, fname, status_msg))
            return

        if vid:
            fname = vid.file_name or 'video.mp4'
            dest  = gifs_dir / f'{user_id}_{ts}_{fname}'
            status_msg = await message.answer('⬇️ <b>Скачиваю файл…</b>', parse_mode='HTML')
            await download_file(vid, dest)
            _sz = dest.stat().st_size / (1024 * 1024) if dest.exists() else None
            await _edit_status(status_msg, filename=fname, size_mb=_sz, step=0)
            asyncio.create_task(_maybe_start_prepare_task(dest, fname, status_msg))
            return

        if doc:
            fname = doc.file_name or 'file'
            mime  = (doc.mime_type or '').lower()
            if fname.lower().endswith(('.gif', '.mp4', '.webm')) or 'gif' in mime or mime.startswith('video'):
                dest  = gifs_dir / f'{user_id}_{ts}_{fname}'
                status_msg = await message.answer('⬇️ <b>Скачиваю файл…</b>', parse_mode='HTML')
                await download_file(doc, dest)
                _sz = dest.stat().st_size / (1024 * 1024) if dest.exists() else None
                await _edit_status(status_msg, filename=fname, size_mb=_sz, step=0)
                asyncio.create_task(_maybe_start_prepare_task(dest, fname, status_msg))
                return
            else:
                await message.answer(
                    f'⚠️ <b>Неподдерживаемый формат</b>\n\n'
                    f'Файл: <code>{_esc(fname)}</code> (<code>{_esc(mime or "—")}</code>)\n\n'
                    f'Отправь <b>GIF-анимацию</b> или <b>MP4-видео</b>.',
                    parse_mode='HTML',
                )
                return

        await message.answer(
            '📎 <b>Файл не найден</b>\n\n'
            'Пожалуйста, отправь GIF-анимацию или MP4-видео.',
            parse_mode='HTML',
        )

    except Exception as e:
        logger.exception('Ошибка при сохранении файла')
        await message.answer(
            f'❌ <b>Ошибка при скачивании файла:</b>\n'
            f'<code>{_esc(str(e)[:300])}</code>',
            parse_mode='HTML',
        )


# ─── Отладочные хендлеры ──────────────────────────────────────────────────────

async def _debug_inspect(message: types.Message):
    parts = []
    if getattr(message, 'animation', None):
        parts.append(f"animation (file_name={getattr(message.animation, 'file_name', None)})")
    if message.document:
        parts.append(f"document (file_name={message.document.file_name} mime={message.document.mime_type})")
    if getattr(message, 'video', None):
        parts.append('video')
    if message.photo:
        parts.append('photo')
    if getattr(message, 'sticker', None):
        parts.append('sticker')
    txt = ' | '.join(parts) or '<no media fields>'
    try:
        await message.answer(f'<code>DEBUG: {_esc(txt)}</code>', parse_mode='HTML')
    except Exception:
        pass
    logger.debug('DEBUG message fields: %s', txt)


async def _debug_raw(message: types.Message):
    try:
        info = {
            'message_id': getattr(message, 'message_id', None),
            'from': getattr(getattr(message, 'from_user', None), 'id', None),
            'has_animation': bool(getattr(message, 'animation', None)),
            'has_document': bool(message.document),
            'has_video': bool(getattr(message, 'video', None)),
            'has_photo': bool(message.photo),
            'has_sticker': bool(getattr(message, 'sticker', None)),
        }
        logger.debug('RAW MESSAGE INFO: %s', info)
        if getattr(message, 'animation', None):
            logger.debug('  animation: %s %s', getattr(message.animation, 'file_name', None), getattr(message.animation, 'mime_type', None))
        if message.document:
            logger.debug('  document: %s %s', message.document.file_name, message.document.mime_type)
        if getattr(message, 'video', None):
            logger.debug('  video: %s %s', getattr(message.video, 'file_name', None), getattr(message.video, 'mime_type', None))
    except Exception:
        logger.exception('DEBUG RAW ERROR')


# ─── Регистрация хендлеров ────────────────────────────────────────────────────

try:
    dp.message.register(cmd_start, lambda message: (message.text or '').strip().startswith('/start'))
    logger.info('Registered cmd_start handler')

    dp.message.register(cmd_help, lambda message: (message.text or '').strip().startswith('/help'))
    logger.info('Registered cmd_help handler')

    def is_media_message(message):
        has_animation = bool(getattr(message, 'animation', None))
        has_document  = bool(message.document)
        has_video     = bool(getattr(message, 'video', None))
        result = has_animation or has_document or has_video
        if result:
            logger.debug('Media filter matched: animation=%s document=%s video=%s', has_animation, has_document, has_video)
        return result

    dp.message.register(handle_file, is_media_message)
    logger.info('Registered handle_file handler')

    dp.callback_query.register(handle_callback, lambda cb: cb.data in ('help', 'about_showcase'))
    logger.info('Registered handle_callback handler')

except Exception as e:
    logger.exception('Failed to register main handlers')
    try:
        dp.message.register(cmd_start)
        dp.message.register(cmd_help)
        dp.message.register(handle_file)
        logger.info('Registered handlers using fallback method')
    except Exception:
        logger.error('Failed to register handlers even with fallback')

if DEBUG_MODE:
    try:
        dp.message.register(_debug_inspect, lambda message: bool(
            getattr(message, 'animation', None) or message.document or
            getattr(message, 'video', None) or message.photo or getattr(message, 'sticker', None)
        ))
        logger.info('Registered _debug_inspect handler')
    except Exception:
        try:
            dp.message.register(_debug_inspect)
        except Exception:
            pass

if DEBUG_MODE:
    try:
        dp.message.register(_debug_raw, lambda message: True)
        logger.info('Registered _debug_raw handler')
    except Exception:
        try:
            dp.message.register(_debug_raw)
        except Exception:
            pass


# ─── Точка входа ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if not TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN not set')

    async def _main():
        try:
            logger.info('Starting polling...')
            await dp.start_polling(bot)
        finally:
            await bot.session.close()

    asyncio.run(_main())
