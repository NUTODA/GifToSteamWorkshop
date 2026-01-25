import os
import asyncio
from pathlib import Path
import logging
import shutil

from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
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

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher(storage=MemoryStorage())
DEBUG_MODE = (LOG_LEVEL or '').upper() == 'DEBUG' or os.getenv('BOT_DEBUG', '') == '1'


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
        await message.answer(f'DEBUG: {txt}')
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
        if message.photo:
            logger.debug('  photo sizes: %s', [ (p.file_id, p.width, p.height) for p in message.photo ])
    except Exception as e:
        logger.exception('DEBUG RAW ERROR')


async def _always_reply(message: types.Message):
    # Aggressive fallback for debugging: always reply so user sees bot is alive
    try:
        logger.debug('ALWAYS_REPLY: replying to message %s', getattr(message, 'message_id', None))
        await message.answer('ACK — message received (debug handler).')
    except Exception as e:
        logger.exception('ALWAYS_REPLY error')


def _save_to_gifs(src_path: Path, message: types.Message, gifs_dir: Path, orig_name: str | None = None) -> Path:
    """
    Copy the uploaded gif (src_path) into gifs_dir with a unique name and return the dest path.
    """
    try:
        gifs_dir.mkdir(exist_ok=True)
    except Exception:
        pass
    import datetime, shutil
    user_id = getattr(message.from_user, 'id', 'unknown')
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    name = orig_name or src_path.name
    # ensure filename has an extension
    if not Path(name).suffix:
        name = f'{name}.gif'
    dest = gifs_dir / f'{user_id}_{ts}_{name}'
    try:
        shutil.copy2(src_path, dest)
        logger.info('Saved uploaded GIF to %s', dest)
        return dest
    except Exception as e:
        logger.exception('Ошибка при сохранении gif')
        return dest


async def cmd_start(message: types.Message):
    logger.info('cmd_start: message_id=%s from=%s text=%s', 
                getattr(message, 'message_id', None),
                getattr(getattr(message, 'from_user', None), 'id', None),
                (message.text or '')[:50])
    text = (message.text or '').strip()
    if not text or not text.lstrip().startswith('/'):
        return
    # accept '/start' with or without bot username and optional args
    cmd = text.split()[0].lstrip('/')
    if cmd.split('@')[0].lower() != 'start':
        return

    await message.answer('Привет! Пришли GIF, и я сохраню его локально.')


async def handle_file(message: types.Message):
    """Save GIF/video files locally. Works with aiogram 3.x API."""
    import datetime
    
    gifs_dir = Path(__file__).parent / 'gifs'
    gifs_dir.mkdir(exist_ok=True)
    
    user_id = getattr(message.from_user, 'id', 'unknown')
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Get file info for logging
    anim = getattr(message, 'animation', None)
    doc = message.document
    vid = getattr(message, 'video', None)
    
    anim_name = getattr(anim, 'file_name', None) if anim else None
    doc_name = getattr(doc, 'file_name', None) if doc else None
    doc_mime = getattr(doc, 'mime_type', None) if doc else None
    video_name = getattr(vid, 'file_name', None) if vid else None
    
    logger.info('handle_file: msg_id=%s from=%s anim=%s doc=%s video=%s anim_name=%s doc_name=%s doc_mime=%s',
                message.message_id, user_id,
                bool(anim), bool(doc), bool(vid),
                anim_name, doc_name, doc_mime)
    
    # Helper function to download file using aiogram 3.x API
    async def download_file(file_obj, dest_path: Path):
        """Download file using bot.download() - aiogram 3.x way"""
        file_id = file_obj.file_id
        logger.debug('Downloading file_id=%s to %s', file_id, dest_path)
        await bot.download(file_id, destination=dest_path)
        logger.info('Downloaded to %s (%d bytes)', dest_path, dest_path.stat().st_size)
        return dest_path
    
    try:
        # Priority: animation > video > document
        # Telegram sends GIFs as animation with video/mp4 mime type

        async def _maybe_start_prepare_task(src_path: Path, visible_name: str):
            """Run prepare_and_resize_copy in executor and notify user on finish/error."""
            if not FFMPEG_UTILS_AVAILABLE:
                logger.debug('FFmpeg utils not available; skipping prepare task')
                return
            # check that ffmpeg executable is available
            try:
                if not is_ffmpeg_available():
                    logger.warning('ffmpeg executable not found; skipping prepare task')
                    # удаляем скачанный файл — обработка невозможна
                    try:
                        if src_path.exists():
                            src_path.unlink()
                            logger.info('Removed upload %s because ffmpeg is unavailable', src_path)
                    except Exception:
                        logger.exception('Failed to remove upload %s when ffmpeg missing', src_path)
                    try:
                        await message.answer('FFmpeg не найден; обработка пропущена и файл удалён. Установите ffmpeg и добавьте его в PATH или задайте переменную окружения FFMPEG_BIN.')
                    except Exception:
                        pass
                    return
            except Exception:
                # defensive: if is_ffmpeg_available raises for some reason, skip and remove upload
                logger.exception('Error checking ffmpeg availability')
                try:
                    if src_path.exists():
                        src_path.unlink()
                        logger.info('Removed upload %s due to ffmpeg check error', src_path)
                except Exception:
                    logger.exception('Failed to remove upload %s after ffmpeg check error', src_path)
                return

            if src_path.suffix.lower() != '.mp4':
                logger.debug('Source not mp4, skipping prepare task: %s', src_path)
                # удаляем скачанный неподходящий файл
                try:
                    if src_path.exists():
                        src_path.unlink()
                        logger.info('Removed non-mp4 upload %s', src_path)
                except Exception:
                    logger.exception('Failed to remove non-mp4 upload %s', src_path)
                try:
                    await message.answer('Файл неподдерживаемого формата был удалён. Отправьте GIF или видео в поддерживаемом формате.')
                except Exception:
                    pass
                return
            prepared_dir = Path(__file__).parent / 'prepared_gifs'
            loop = asyncio.get_running_loop()
            try:
                # prepare_and_resize_copy may be None if ffmpeg helpers failed to import; assert to make intent explicit
                assert prepare_and_resize_copy is not None
                prepared = await loop.run_in_executor(None, prepare_and_resize_copy, src_path, prepared_dir)
                try:
                    await message.answer(f'Подготовлено: {visible_name}')
                except Exception:
                    pass

                # Теперь копируем подготовленный файл в sliced_gifs и запускаем нарезку
                try:
                    slised_dir = Path(__file__).parent / 'sliced_gifs'
                    slised_dir.mkdir(exist_ok=True)
                    slised_copy = slised_dir / prepared.name
                    shutil.copy2(prepared, slised_copy)
                    logger.info('Copied prepared file to %s for slicing', slised_copy)

                    if slice_video_inplace_with_gifs:
                        # Run slicing in executor and handle errors locally
                        try:
                            archive_path = await loop.run_in_executor(None, slice_video_inplace_with_gifs, slised_copy)
                        except Exception as e:
                            logger.exception('Ошибка при нарезке файла %s', slised_copy)
                            # Attempt to clean up any artifacts: slised_copy, partial gifs, prepared, original uploaded
                            try:
                                if slised_copy.exists():
                                    slised_copy.unlink()
                                    logger.info('Removed slised copy %s after failed slicing', slised_copy)
                            except Exception:
                                logger.exception('Failed to remove slised_copy %s', slised_copy)
                            try:
                                for f in slised_dir.glob(f"{slised_copy.stem}*"):
                                    try:
                                        if f.is_dir():
                                            shutil.rmtree(f)
                                        else:
                                            f.unlink()
                                        logger.info('Removed artifact %s', f)
                                    except Exception:
                                        logger.exception('Failed to remove artifact %s', f)
                            except Exception:
                                logger.exception('Error while cleaning artifacts in %s', slised_dir)
                            try:
                                if prepared.exists():
                                    prepared.unlink()
                                    logger.info('Removed prepared file %s after failed slicing', prepared)
                            except Exception:
                                logger.exception('Failed to remove prepared file %s', prepared)
                            try:
                                if src_path.exists():
                                    src_path.unlink()
                                    logger.info('Removed original upload %s after failed slicing', src_path)
                            except Exception:
                                logger.exception('Failed to remove original upload %s', src_path)
                            try:
                                await message.answer(f'Ошибка при создании GIFов: {e}')
                            except Exception:
                                pass
                            return

                        # Если нарезка прошла успешно — удаляем промежуточные файлы
                        try:
                            if src_path.exists():
                                src_path.unlink()
                                logger.info('Removed original upload %s', src_path)
                        except Exception:
                            logger.exception('Failed to remove original upload %s', src_path)
                            try:
                                await message.answer('Не удалось удалить исходный файл в gifs/ — проверьте права/логи.')
                            except Exception:
                                pass

                        try:
                            if prepared.exists():
                                prepared.unlink()
                                logger.info('Removed prepared file %s', prepared)
                        except Exception:
                            logger.exception('Failed to remove prepared file %s', prepared)
                            try:
                                await message.answer('Не удалось удалить временный файл в prepared_gifs/ — проверьте права/логи.')
                            except Exception:
                                pass

                        # Удаляем все промежуточные .mp4 файлы в папке sliced_gifs, относящиеся к этому файлу
                        try:
                            removed = []
                            for mp4 in slised_dir.glob(f"{slised_copy.stem}*.mp4"):
                                try:
                                    mp4.unlink()
                                    removed.append(mp4.name)
                                except Exception:
                                    logger.exception('Failed to remove intermediate mp4 %s', mp4)
                            if removed:
                                logger.info('Removed intermediate mp4 files in %s: %s', slised_dir, ','.join(removed))
                        except Exception:
                            logger.exception('Error while cleaning .mp4 files in %s', slised_dir)

                        # Если нарезка и архивирование прошли успешно — попытаемся отправить ZIP пользователю
                        try:
                            if archive_path:
                                archive = Path(archive_path)
                                if archive.exists():
                                    try:
                                        await message.answer('Нарезка завершена — отправляю ZIP с GIFами.')
                                    except Exception:
                                        pass
                                    try:
                                        fsfile = FSInputFile(str(archive))
                                        await message.answer_document(document=fsfile, caption=f'Архив GIF-ов: {archive.name}\nСодержит 5 частей для витрины Steam.')
                                        logger.info('Sent ZIP %s to user %s', archive, getattr(message.from_user, 'id', None))
                                    except Exception:
                                        logger.exception('Failed to send ZIP archive %s to user', archive)
                                        try:
                                            await message.answer('Не удалось отправить архив по сети. Архив создан локально.')
                                        except Exception:
                                            pass
                                else:
                                    logger.warning('Archive path returned but file missing: %s', archive_path)
                        except Exception:
                            logger.exception('Unexpected error while attempting to send archive')
                            try:
                                await message.answer('Произошла ошибка при попытке отправить архив — проверьте логи.')
                            except Exception:
                                pass
                    else:
                        logger.debug('slice_video_inplace_with_gifs not available; skipping slicing')
                except Exception as e:
                    logger.exception('Ошибка при подготовке и нарезке файла %s', prepared)
                    try:
                        await message.answer(f'Ошибка при создании GIFов: {e}')
                    except Exception:
                        pass

            except Exception as e:
                logger.exception('Ошибка подготовки файла %s', src_path)
                # Cleanup candidate prepared file and original upload
                try:
                    prep_candidate = prepared_dir / src_path.name
                    if prep_candidate.exists():
                        prep_candidate.unlink()
                        logger.info('Removed prepared candidate %s after preparation error', prep_candidate)
                except Exception:
                    logger.exception('Failed to remove prepared candidate %s', prep_candidate)
                try:
                    if src_path.exists():
                        src_path.unlink()
                        logger.info('Removed original upload %s after preparation error', src_path)
                except Exception:
                    logger.exception('Failed to remove original upload %s', src_path)
                try:
                    await message.answer(f'Ошибка подготовки файла: {e}')
                except Exception:
                    pass

        if anim:
            fname = anim.file_name or 'animation.mp4'
            # Always save with original extension (usually .mp4 for Telegram GIFs)
            dest = gifs_dir / f'{user_id}_{ts}_{fname}'
            await download_file(anim, dest)
            await message.answer(f'GIF сохранён: {dest.name}')
            # start background prepare task (non-blocking)
            asyncio.create_task(_maybe_start_prepare_task(dest, dest.name))
            return
            
        if vid:
            fname = vid.file_name or 'video.mp4'
            dest = gifs_dir / f'{user_id}_{ts}_{fname}'
            await download_file(vid, dest)
            await message.answer(f'Видео сохранено: {dest.name}')
            asyncio.create_task(_maybe_start_prepare_task(dest, dest.name))
            return
            
        if doc:
            fname = doc.file_name or 'file'
            mime = (doc.mime_type or '').lower()
            
            # Accept GIF or video files
            if fname.lower().endswith(('.gif', '.mp4', '.webm')) or 'gif' in mime or mime.startswith('video'):
                dest = gifs_dir / f'{user_id}_{ts}_{fname}'
                await download_file(doc, dest)
                await message.answer(f'Файл сохранён: {dest.name}')
                asyncio.create_task(_maybe_start_prepare_task(dest, dest.name))
                return
            else:
                await message.answer(f'Неподдерживаемый формат: {fname} ({mime}). Отправьте GIF или видео.')
                return
        
        await message.answer('Отправьте GIF-анимацию или видео файл.')
        
    except Exception as e:
        logger.exception('Ошибка при сохранении файла')
        await message.answer(f'Ошибка при сохранении: {e}')


# Register handlers (use explicit registration to be compatible with installed aiogram)
# Register main handlers FIRST before debug handlers
try:
    # Start command handler
    dp.message.register(cmd_start, lambda message: (message.text or '').strip().startswith('/start'))
    logger.info('Registered cmd_start handler')
    
    # File handler - simple filter that checks for animation, document OR video
    def is_media_message(message):
        has_animation = bool(getattr(message, 'animation', None))
        has_document = bool(message.document)
        has_video = bool(getattr(message, 'video', None))
        result = has_animation or has_document or has_video
        if result:
            logger.debug('Media filter matched: animation=%s document=%s video=%s', has_animation, has_document, has_video)
        return result
    
    dp.message.register(handle_file, is_media_message)
    logger.info('Registered handle_file handler')
except Exception as e:
    logger.exception('Failed to register main handlers')
    # fallback: some aiogram versions expect positional filter objects; attempt simple registrations
    try:
        dp.message.register(cmd_start)
        dp.message.register(handle_file)
        logger.info('Registered handlers using fallback method')
    except Exception:
        logger.error('Failed to register handlers even with fallback')

if DEBUG_MODE:
    # Debug: register inspector for media messages AFTER main handlers
    try:
        dp.message.register(_debug_inspect, lambda message: bool(
            getattr(message, 'animation', None) or message.document or getattr(message, 'video', None) or message.photo or getattr(message, 'sticker', None)
        ))
        logger.info('Registered _debug_inspect handler')
    except Exception:
        try:
            dp.message.register(_debug_inspect)
        except Exception:
            pass

if DEBUG_MODE:
    # register raw inspector (catch-all) LAST to log message internals without blocking other handlers
    try:
        dp.message.register(_debug_raw, lambda message: True)
        logger.info('Registered _debug_raw handler')
    except Exception:
        try:
            dp.message.register(_debug_raw)
        except Exception:
            pass


if __name__ == '__main__':
    import logging

    # Use existing logging configuration from early import

    if not TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN not set')

    async def _main():
        try:
            logger.info('Starting polling...')
            await dp.start_polling(bot)
        finally:
            await bot.session.close()

    asyncio.run(_main())
