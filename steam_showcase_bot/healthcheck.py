import sys
import time
from pathlib import Path

from .config import HEARTBEAT_FILE, HEALTHCHECK_MAX_STALENESS_SECONDS
from .ffmpeg_utils import is_ffmpeg_available


def main() -> int:
    heartbeat = Path(HEARTBEAT_FILE)

    if not heartbeat.exists():
        print(f'heartbeat file not found: {heartbeat}')
        return 1

    age_seconds = time.time() - heartbeat.stat().st_mtime
    if age_seconds > HEALTHCHECK_MAX_STALENESS_SECONDS:
        print(
            'heartbeat is stale: '
            f'age={age_seconds:.1f}s max={HEALTHCHECK_MAX_STALENESS_SECONDS}s'
        )
        return 1

    if not is_ffmpeg_available():
        print('ffmpeg is not available')
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
