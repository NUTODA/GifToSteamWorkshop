import asyncio
import datetime
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, Router, types

from ..config import MAX_FILE_SIZE_MB
from ..i18n import get_user_locale, tr
from ..services.processor import ProcessingService
from ..texts import edit_status, esc

logger = logging.getLogger('steam_showcase_bot.handlers.media')

router = Router(name='media')


def _is_media(message: types.Message) -> bool:
    has_animation = bool(getattr(message, 'animation', None))
    has_document = bool(message.document)
    has_video = bool(getattr(message, 'video', None))
    result = has_animation or has_document or has_video
    if result:
        logger.debug(
            'Media filter matched: animation=%s document=%s video=%s',
            has_animation, has_document, has_video,
        )
    return result


def _check_file_size(file_obj) -> tuple[bool, float | None]:
    """Возвращает (ok, size_mb). ok=False если файл превышает лимит."""
    file_size = getattr(file_obj, 'file_size', None)
    if file_size is None:
        return True, None
    size_mb = file_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, size_mb
    return True, size_mb


@router.message(_is_media)
async def handle_file(message: types.Message, bot: Bot, processor: ProcessingService, dispatcher: Dispatcher):
    """Скачивает GIF/видео, создаёт прогресс-сообщение и запускает обработку."""
    gifs_dir = Path(__file__).resolve().parent.parent / 'gifs'
    gifs_dir.mkdir(exist_ok=True)

    user = getattr(message, 'from_user', None)
    user_id = getattr(user, 'id', None)
    locale = await get_user_locale(
        dispatcher,
        bot,
        user_id,
        getattr(user, 'language_code', None),
    )
    owner_id = user_id if user_id is not None else 'unknown'
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    anim = getattr(message, 'animation', None)
    doc = message.document
    vid = getattr(message, 'video', None)

    logger.info(
        'handle_file: msg_id=%s from=%s anim=%s doc=%s video=%s',
        message.message_id, user_id, bool(anim), bool(doc), bool(vid),
    )

    async def _download_and_process(file_obj, fname: str):
        if dispatcher.workflow_data.get('is_stopping'):
            await message.answer(
                tr('media_stopping', locale),
                parse_mode='HTML',
            )
            return

        ok, size_mb = _check_file_size(file_obj)
        if not ok:
            await message.answer(
                tr(
                    'media_file_too_big',
                    locale,
                    size_mb=f'{size_mb:.1f}',
                    max_mb=MAX_FILE_SIZE_MB,
                ),
                parse_mode='HTML',
            )
            return

        dest = gifs_dir / f'{owner_id}_{ts}_{fname}'
        status_msg = await message.answer(tr('media_downloading', locale), parse_mode='HTML')
        await bot.download(file_obj.file_id, destination=dest)
        logger.info('Downloaded to %s (%d bytes)', dest, dest.stat().st_size)

        _sz = dest.stat().st_size / (1024 * 1024) if dest.exists() else None
        await edit_status(status_msg, filename=fname, size_mb=_sz, step=0, locale=locale)
        task = asyncio.create_task(processor.process_file(dest, fname, message, status_msg, locale))
        active_tasks = dispatcher.workflow_data.get('active_processing_tasks')
        if isinstance(active_tasks, set):
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)

    try:
        if anim:
            fname = anim.file_name or 'animation.mp4'
            await _download_and_process(anim, fname)
            return

        if vid:
            fname = vid.file_name or 'video.mp4'
            await _download_and_process(vid, fname)
            return

        if doc:
            fname = doc.file_name or 'file'
            mime = (doc.mime_type or '').lower()
            if fname.lower().endswith(('.gif', '.mp4', '.webm')) or 'gif' in mime or mime.startswith('video'):
                await _download_and_process(doc, fname)
                return
            else:
                await message.answer(
                    tr(
                        'media_unsupported_format',
                        locale,
                        filename=esc(fname),
                        mime=esc(mime or '-'),
                    ),
                    parse_mode='HTML',
                )
                return

        await message.answer(
            tr('media_file_not_found', locale),
            parse_mode='HTML',
        )

    except Exception as e:
        logger.exception('Error while saving file')
        await message.answer(
            tr('media_download_error', locale, error=esc(str(e)[:300])),
            parse_mode='HTML',
        )
