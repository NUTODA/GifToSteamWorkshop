import os
import subprocess
from pathlib import Path
import logging
import shutil
import json

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

    input_str = str(Path(input_path))
    output_str = str(Path(output_path))

    cmd = [
        FFMPEG_BIN,
        "-y",  # перезаписывать выходной файл
        "-i", input_str,
        "-vf", "scale='if(gt(iw,750),750,iw)':-2",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
    ]

    # добавляем выход в конце
    cmd.append(output_str)

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

# --- Additional utilities: probe, gif creation, and slicing into parts ---

# detect ffprobe binary similarly to ffmpeg
FFPROBE_BIN = os.environ.get('FFPROBE_BIN') or shutil.which('ffprobe') or (os.path.join(os.path.dirname(FFMPEG_BIN), 'ffprobe') if FFMPEG_BIN and os.path.dirname(FFMPEG_BIN) else None)

def is_ffprobe_available() -> bool:
    """Return True if ffprobe is available."""
    return bool(FFPROBE_BIN)


def get_width_height(path: Path):
    """Return (width, height) of first video stream using ffprobe. Raises RuntimeError if ffprobe missing or probe fails."""
    if not is_ffprobe_available():
        raise RuntimeError("ffprobe не найден: установите ffprobe и добавьте его в PATH или задайте переменную окружения FFPROBE_BIN.")
    cmd = [
        FFPROBE_BIN, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", str(path)
    ]
    try:
        out = subprocess.check_output(cmd, text=True)
        data = json.loads(out)
        w = data["streams"][0]["width"]
        h = data["streams"][0]["height"]
        return w, h
    except Exception as e:
        logger.error('ffprobe failed: %s', e)
        raise RuntimeError(f"ffprobe error: {e}") from e


def make_gif_from_video(input_path: Path, output_gif: Path, fps: int = 15, scale_w: int = -1):
    """Create an optimized GIF from a video using ffmpeg. scale_w=-1 keeps width."""
    if not is_ffmpeg_available():
        raise RuntimeError("ffmpeg не найден: установите ffmpeg и добавьте его в PATH или задайте переменную окружения FFMPEG_BIN.")
    vf = f"fps={fps},scale={scale_w}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
    cmd = [
        FFMPEG_BIN, "-y", "-i", str(input_path),
        "-vf", vf,
        str(output_gif)
    ]
    logger.debug('Running ffmpeg for GIF: %s', ' '.join(cmd))
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        logger.error('ffmpeg GIF creation failed: %s', e)
        raise

    # После создания GIF проверяем последний байт и при необходимости заменяем 0x3B на 0x21
    try:
        _fix_gif_terminator(output_gif)
    except Exception:
        logger.exception('Failed to adjust GIF terminator for %s', output_gif)


def _fix_gif_terminator(gif_path: Path) -> bool:
    """If last byte of GIF is 0x3B, replace it with 0x21. Returns True if changed."""
    p = Path(gif_path)
    try:
        with p.open('r+b') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                logger.debug('GIF file %s is empty, skipping terminator fix', p)
                return False
            # read last byte
            f.seek(-1, os.SEEK_END)
            last = f.read(1)
            if last == b'\x3B':
                f.seek(-1, os.SEEK_END)
                f.write(b'\x21')
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
                logger.info('Replaced GIF terminator for %s: 0x3B -> 0x21', p)
                return True
            else:
                logger.debug('GIF terminator is %s for %s; no change', last.hex() if last else None, p)
                return False
    except Exception as e:
        logger.exception('Error adjusting GIF terminator for %s: %s', gif_path, e)
        raise


def slice_video_inplace_with_gifs(path: str | Path):
    """Slice a 750px-wide video into five 150px-wide parts.

    Replaces the original file with the first part (inplace), writes parts 2..5 as separate files
    next to the input, and creates a directory <stem>_gifs with part1.gif..part5.gif.
    """
    p = Path(path)
    w, h = get_width_height(p)
    if w != 750:
        raise ValueError(f"Ожидалась ширина 750px, получено {w}px")

    part_w = 150

    # Temporary file for the first part so we can replace the original safely
    tmp_first = p.with_name(f"{p.stem}__tmp_part1{p.suffix}")

    part_paths = []

    # Нарезка на 5 частей
    for i in range(5):
        x = i * part_w
        out = tmp_first if i == 0 else p.with_name(f"{p.stem}_part{i+1}{p.suffix}")
        cmd = [
            FFMPEG_BIN, "-y", "-i", str(p),
            "-vf", f"crop={part_w}:{h}:{x}:0",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "copy",
            str(out)
        ]
        logger.debug('Running ffmpeg for slice: %s', ' '.join(cmd))
        subprocess.check_call(cmd)
        part_paths.append(out)

    # Перезаписываем исходник первой частью
    tmp_first.replace(p)
    part_paths[0] = p  # обновляем путь первой части

    # Создаём директорию для GIF
    gif_dir = p.with_name(f"{p.stem}_gifs")
    gif_dir.mkdir(exist_ok=True)

    # Делаем 5 GIF-ов
    for i, part in enumerate(part_paths, start=1):
        gif_path = gif_dir / f"part{i}.gif"
        logger.info('Creating GIF %s from %s', gif_path, part)
        make_gif_from_video(part, gif_path, fps=15, scale_w=-1)

    logger.info('Slicing complete. GIFs are in %s', gif_dir)

    # Archive the GIFs into a ZIP file placed next to the sliced files (in sliced_gifs/),
    # then remove the intermediate GIF files to save space.
    try:
        zip_base = str(p.with_name(f"{p.stem}_gifs"))  # without .zip suffix
        archive_path = shutil.make_archive(zip_base, 'zip', root_dir=str(gif_dir))
        logger.info('Created ZIP archive of GIFs at %s', archive_path)
        try:
            shutil.rmtree(gif_dir)
            logger.info('Removed intermediate GIF directory %s after archiving', gif_dir)
        except Exception:
            logger.exception('Failed to remove GIF directory %s after archiving', gif_dir)
        # Return the path to archive for potential callers
        return Path(archive_path)
    except Exception:
        logger.exception('Failed to create ZIP archive for GIFs in %s; leaving GIF files in place', gif_dir)
        return None