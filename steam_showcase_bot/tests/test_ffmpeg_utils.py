import tempfile
from pathlib import Path

import steam_showcase_bot.ffmpeg_utils as ffmpeg_utils


class _DummyPopen:
    def __init__(self, cmd, stdout=None, stderr=None, text=None):
        self.cmd = cmd
        self.args = cmd
        self.stdout = stdout
        self.stderr = stderr
        self.text = text
        self.returncode = 0
        self._out = ''
        self._err = ''

    def communicate(self, input=None, timeout=None):
        return self._out, self._err

    def wait(self, timeout=None):
        return self.returncode

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -9

    def terminate(self):
        self.returncode = -15

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyPopenFail(_DummyPopen):
    def __init__(self, cmd, stdout=None, stderr=None, text=None):
        super().__init__(cmd, stdout=stdout, stderr=stderr, text=text)
        self.returncode = 1
        self._err = 'ffmpeg failed'


def _patch_attr(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    return old


def test_fix_gif_terminator_replaces_last_byte():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'test.gif'
        path.write_bytes(b'GIF89aDATA\x3B')

        changed = ffmpeg_utils._fix_gif_terminator(path)

        assert changed is True
        assert path.read_bytes()[-1:] == b'\x21'


def test_fix_gif_terminator_keeps_non_standard_last_byte():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'test.gif'
        path.write_bytes(b'GIF89aDATA\x21')

        changed = ffmpeg_utils._fix_gif_terminator(path)

        assert changed is False
        assert path.read_bytes()[-1:] == b'\x21'


def test_fix_gif_terminator_empty_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'empty.gif'
        path.write_bytes(b'')

        changed = ffmpeg_utils._fix_gif_terminator(path)

        assert changed is False
        assert path.read_bytes() == b''


def test_resize_mp4_to_width_750_success():
    old_bin = _patch_attr(ffmpeg_utils, 'FFMPEG_BIN', 'ffmpeg')
    old_popen = _patch_attr(ffmpeg_utils.subprocess, 'Popen', _DummyPopen)
    try:
        ffmpeg_utils.resize_mp4_to_width_750(Path('in.mp4'), Path('out.mp4'))
    finally:
        ffmpeg_utils.FFMPEG_BIN = old_bin
        ffmpeg_utils.subprocess.Popen = old_popen


def test_resize_mp4_to_width_750_raises_on_ffmpeg_error():
    old_bin = _patch_attr(ffmpeg_utils, 'FFMPEG_BIN', 'ffmpeg')
    old_popen = _patch_attr(ffmpeg_utils.subprocess, 'Popen', _DummyPopenFail)
    try:
        raised = False
        try:
            ffmpeg_utils.resize_mp4_to_width_750(Path('in.mp4'), Path('out.mp4'))
        except RuntimeError as exc:
            raised = 'ffmpeg error' in str(exc)
        assert raised
    finally:
        ffmpeg_utils.FFMPEG_BIN = old_bin
        ffmpeg_utils.subprocess.Popen = old_popen


def test_make_gif_from_video_invokes_terminator_fix():
    old_bin = _patch_attr(ffmpeg_utils, 'FFMPEG_BIN', 'ffmpeg')
    old_popen = _patch_attr(ffmpeg_utils.subprocess, 'Popen', _DummyPopen)
    called = {'value': False}

    def _fake_fix(path):
        called['value'] = True
        return True

    old_fix = _patch_attr(ffmpeg_utils, '_fix_gif_terminator', _fake_fix)
    try:
        ffmpeg_utils.make_gif_from_video(Path('in.mp4'), Path('out.gif'))
        assert called['value'] is True
    finally:
        ffmpeg_utils.FFMPEG_BIN = old_bin
        ffmpeg_utils.subprocess.Popen = old_popen
        ffmpeg_utils._fix_gif_terminator = old_fix


def test_make_gif_from_video_raises_when_ffmpeg_missing():
    old_bin = _patch_attr(ffmpeg_utils, 'FFMPEG_BIN', None)
    try:
        raised = False
        try:
            ffmpeg_utils.make_gif_from_video(Path('in.mp4'), Path('out.gif'))
        except RuntimeError as exc:
            raised = 'ffmpeg не найден' in str(exc)
        assert raised
    finally:
        ffmpeg_utils.FFMPEG_BIN = old_bin
