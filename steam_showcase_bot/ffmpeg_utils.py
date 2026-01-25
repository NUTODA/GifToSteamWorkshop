import os
import subprocess
from pathlib import Path
import logging
import shutil

logger = logging.getLogger('steam_showcase_bot.ffmpeg_utils')

# detect ffmpeg binary: prefer FFMPEG_BIN env var, fallback to PATH lookup
FFMPEG_BIN = os.environ.get('FFMPEG_BIN') or shutil.which('ffmpeg')

def is_ffmpeg_available() -> bool:
    """Return True if an ffmpeg executable is available (or FFMPEG_BIN set)."""
    return bool(FFMPEG_BIN)


def resize_mp4_to_width_750(input_path: Path, output_path: Path) -> None:
    """
    Уменьшает ширину видео до 750px (если больше), не кропает,
    сохраняет пропорции, качество высокое (H.264, CRF 18).

    input_path/output_path могут быть str или Path. Функция бросает
    RuntimeError при ошибке ffmpeg или если ffmpeg не найден.
    """
    if not is_ffmpeg_available():
        raise RuntimeError("ffmpeg не найден: установите ffmpeg и добавьте его в PATH или задайте переменную окружения FFMPEG_BIN.")

    input_path = str(Path(input_path))
    output_path = str(Path(output_path))

    cmd = [
        FFMPEG_BIN,
        "-y",  # перезаписывать выходной файл
        "-i", input_path,
        "-vf", "scale='if(gt(iw,750),750,iw)':-2",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
    ]

    # добавляем выход в конце
    cmd.append(output_path)

    logger.debug('Running ffmpeg command: %s', ' '.join(cmd))
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as e:
        logger.error('ffmpeg executable not found: %s', e)
        raise RuntimeError("ffmpeg executable not found: убедитесь, что ffmpeg доступен в PATH или задайте FFMPEG_BIN.") from e

    if result.returncode != 0:
        logger.error('ffmpeg failed: %s', result.stderr)
        raise RuntimeError(f"ffmpeg error:\n{result.stderr}")


def prepare_and_resize_copy(src_path: Path, prepared_dir: Path) -> Path:
    """
    Скопировать src_path в prepared_dir, затем выполнить resize
    и заменить скопированный файл результатом обработки.

    Возвращает путь к подготовленному (обработанному) файлу.
    """
    prepared_dir.mkdir(parents=True, exist_ok=True)
    dest = prepared_dir / src_path.name

    # copy original into prepared dir
    shutil.copy2(src_path, dest)
    logger.info('Copied %s -> %s', src_path, dest)

    # only process mp4 files
    if dest.suffix.lower() != '.mp4':
        logger.info('Skipping ffmpeg resize for non-mp4 file: %s', dest)
        return dest

    tmp_out = dest.with_name(dest.stem + '_750w' + dest.suffix)
    try:
        resize_mp4_to_width_750(dest, tmp_out)
        # replace original copied file with resized output
        tmp_out.replace(dest)
        logger.info('Resized and replaced %s', dest)
        return dest
    except Exception:
        # on failure, attempt to remove tmp_out if exists
        try:
            if tmp_out.exists():
                tmp_out.unlink()
        except Exception:
            pass
        raise
