import asyncio
import logging
import shutil
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import FSInputFile, Message

from ..config import MAX_ARCHIVE_SEND_MB, ZIP_SEND_RETRIES, ZIP_SEND_TIMEOUT
from ..ffmpeg_utils import (
    is_ffmpeg_available,
    prepare_and_resize_copy,
    slice_video_inplace_with_gifs,
)
from ..i18n import tr
from ..texts import (
    STEP_DONE,
    STEP_GIFS,
    STEP_SCALE,
    STEP_SLICE,
    edit_status,
    esc,
)

logger = logging.getLogger('steam_showcase_bot.processor')


class ProcessingService:
    def __init__(self, bot: Bot, semaphore: asyncio.Semaphore):
        self._bot = bot
        self._semaphore = semaphore

    async def process_file(
        self,
        src_path: Path,
        visible_name: str,
        message: Message,
        status_msg: Message | None,
        locale: str,
    ) -> None:
        """Полный цикл: resize -> slice -> GIF -> ZIP -> отправка -> cleanup.

        Автоматически захватывает семафор, ограничивая параллельные задачи ffmpeg.
        """
        async with self._semaphore:
            await self._do_process(src_path, visible_name, message, status_msg, locale)

    async def _do_process(
        self,
        src_path: Path,
        visible_name: str,
        message: Message,
        status_msg: Message | None,
        locale: str,
    ) -> None:
        user_id = getattr(message.from_user, 'id', 'unknown')
        _sz: float | None = None
        try:
            _sz = src_path.stat().st_size / (1024 * 1024)
        except Exception:
            pass

        async def _upd(step: int, failed_at: int | None = None, error_msg: str | None = None):
            await edit_status(
                status_msg, filename=visible_name, size_mb=_sz,
                step=step, failed_at=failed_at, error_msg=error_msg, locale=locale,
            )

        if not is_ffmpeg_available():
            logger.warning('ffmpeg executable not found; skipping prepare task')
            await _upd(0, failed_at=STEP_SCALE, error_msg='FFmpeg не найден на сервере')
            self._safe_unlink(src_path)
            try:
                await message.answer(
                    tr('processor_ffmpeg_missing', locale),
                    parse_mode='HTML',
                )
            except Exception:
                pass
            return

        if src_path.suffix.lower() != '.mp4':
            logger.debug('Source not mp4, skipping: %s', src_path)
            await _upd(0, failed_at=STEP_SCALE, error_msg='Неподдерживаемый формат файла')
            self._safe_unlink(src_path)
            try:
                await message.answer(
                    tr(
                        'processor_unsupported_format',
                        locale,
                        filename=esc(visible_name),
                    ),
                    parse_mode='HTML',
                )
            except Exception:
                pass
            return

        prepared_dir = src_path.parent.parent / 'prepared_gifs'
        loop = asyncio.get_running_loop()

        try:
            await _upd(STEP_SCALE)
            prepared = await loop.run_in_executor(None, prepare_and_resize_copy, src_path, prepared_dir)

            sliced_dir = src_path.parent.parent / 'sliced_gifs'
            sliced_dir.mkdir(exist_ok=True)
            sliced_copy = sliced_dir / prepared.name
            shutil.copy2(prepared, sliced_copy)
            logger.info('Copied prepared file to %s for slicing', sliced_copy)

            await _upd(STEP_SLICE)
            try:
                archive_path = await loop.run_in_executor(None, slice_video_inplace_with_gifs, sliced_copy)
            except Exception as e:
                logger.exception('Error while slicing file %s', sliced_copy)
                await _upd(0, failed_at=STEP_GIFS, error_msg=str(e))
                for path in (sliced_copy, prepared, src_path):
                    self._safe_unlink(path)
                self._clean_artifacts(sliced_dir, sliced_copy.stem)
                try:
                    await message.answer(
                        tr('processor_gif_error', locale, error=esc(str(e)[:300])),
                        parse_mode='HTML',
                    )
                except Exception:
                    pass
                return

            for path in (src_path, prepared):
                self._safe_unlink(path)

            self._clean_mp4_artifacts(sliced_dir, sliced_copy.stem)

            await _upd(STEP_DONE)
            await self._send_archive(archive_path, message, user_id, locale)

        except Exception as e:
            logger.exception('Error while preparing file %s', src_path)
            await _upd(0, failed_at=STEP_SCALE, error_msg=str(e))
            for path in (prepared_dir / src_path.name, src_path):
                self._safe_unlink(path)
            try:
                await message.answer(
                    tr('processor_scale_error', locale, error=esc(str(e)[:300])),
                    parse_mode='HTML',
                )
            except Exception:
                pass

    async def _send_archive(self, archive_path, message: Message, user_id, locale: str) -> None:
        if not archive_path:
            logger.debug('No archive path returned; skipping send')
            return

        archive = Path(archive_path)
        if not archive.exists():
            logger.warning('Archive path returned but file missing: %s', archive_path)
            return

        size_mb = archive.stat().st_size / (1024 * 1024)
        if size_mb > MAX_ARCHIVE_SEND_MB:
            logger.warning('Archive %s is too large (%.1f MB), limit %d MB', archive, size_mb, MAX_ARCHIVE_SEND_MB)
            try:
                await message.answer(
                    tr(
                        'processor_archive_too_big',
                        locale,
                        size_mb=f'{size_mb:.1f}',
                        max_mb=MAX_ARCHIVE_SEND_MB,
                    ),
                    parse_mode='HTML',
                )
            except Exception:
                pass
            return

        sent = False
        for attempt in range(1, ZIP_SEND_RETRIES + 1):
            try:
                fsfile = FSInputFile(str(archive))
                caption = tr('processor_archive_caption', locale, size_mb=f'{size_mb:.1f}')
                await message.answer_document(
                    document=fsfile,
                    caption=caption,
                    parse_mode='HTML',
                    request_timeout=ZIP_SEND_TIMEOUT,
                )
                logger.info(
                    'Sent ZIP %s to user %s (size=%.1f MB) on attempt %d',
                    archive, user_id, size_mb, attempt,
                )
                sent = True
                break
            except TelegramNetworkError as e:
                logger.warning('Attempt %d: TelegramNetworkError sending %s: %s', attempt, archive, e)
                if attempt < ZIP_SEND_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.exception('Failed to send ZIP %s after %d attempts', archive, ZIP_SEND_RETRIES)
                    try:
                        await message.answer(
                            tr('processor_send_failed_network', locale),
                            parse_mode='HTML',
                        )
                    except Exception:
                        pass
            except Exception:
                logger.exception('Failed to send ZIP %s', archive)
                try:
                    await message.answer(
                        tr('processor_send_failed_generic', locale),
                        parse_mode='HTML',
                    )
                except Exception:
                    pass
                break

        if not sent:
            logger.warning('Archive %s was not delivered to user %s', archive, user_id)

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
                logger.info('Removed %s', path)
        except Exception:
            logger.exception('Failed to remove %s', path)

    @staticmethod
    def _clean_artifacts(sliced_dir: Path, stem: str) -> None:
        try:
            for f in sliced_dir.glob(f'{stem}*'):
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

    @staticmethod
    def _clean_mp4_artifacts(sliced_dir: Path, stem: str) -> None:
        try:
            removed = []
            for mp4 in sliced_dir.glob(f'{stem}*.mp4'):
                try:
                    mp4.unlink()
                    removed.append(mp4.name)
                except Exception:
                    logger.exception('Failed to remove intermediate mp4 %s', mp4)
            if removed:
                logger.info('Removed intermediate mp4 files: %s', ', '.join(removed))
        except Exception:
            logger.exception('Error while cleaning .mp4 files in %s', sliced_dir)
