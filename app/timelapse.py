import logging
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
FRAMES_DIR = ROOT / 'timelapse_frames'

_lock = threading.Lock()
_stop = threading.Event()

_state = {
    'status':   'idle',   # idle | capturing | building | done | error
    'captured': 0,
    'total':    0,
    'message':  '',
    'video':    '',
}


def status() -> dict:
    with _lock:
        return dict(_state)


def start(interval: float, duration_min: float, fps: int = 10) -> tuple:
    with _lock:
        if _state['status'] in ('capturing', 'building'):
            return False, 'Already running'
    _stop.clear()
    threading.Thread(
        target=_run, args=(interval, duration_min, fps), daemon=True
    ).start()
    return True, ''


def stop():
    _stop.set()


def _update(**kwargs):
    with _lock:
        _state.update(kwargs)


def _run(interval: float, duration_min: float, fps: int):
    from . import camera

    total = max(1, int(duration_min * 60 / interval))
    run_ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    frames_dir = FRAMES_DIR / run_ts
    frames_dir.mkdir(parents=True, exist_ok=True)

    _update(status='capturing', total=total, captured=0, message='', video='')

    camera.stop()
    time.sleep(0.5)  # let camera hardware fully release
    captured = 0
    try:
        from picamera2 import Picamera2
        cam = Picamera2()
        cam.configure(cam.create_still_configuration(main={'size': (1920, 1080)}))
        cam.start()
        try:
            while captured < total and not _stop.is_set():
                ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                cam.capture_file(str(frames_dir / f'frame_{ts}.jpg'))
                captured += 1
                _update(captured=captured)
                if captured < total:
                    _stop.wait(interval)
        finally:
            cam.stop()
    except Exception as exc:
        logger.error('Capture error: %s', exc)
        camera.start()
        _update(status='error', message=str(exc))
        return

    camera.start()

    if captured == 0:
        _update(status='idle', message='Stopped before any frames captured')
        return

    _update(status='building', message=f'Building video from {captured} frames…')

    video_name = f'timelapse_{run_ts}.mp4'
    video_path = ROOT / video_name
    try:
        result = subprocess.run([
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-pattern_type', 'glob',
            '-i', str(frames_dir / '*.jpg'),
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '28', '-pix_fmt', 'yuv420p',
            str(video_path),
        ], capture_output=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode()[-300:])

        for f in frames_dir.glob('*.jpg'):
            f.unlink()
        frames_dir.rmdir()

        _update(status='done', message='', video=video_name)
        logger.info('Timelapse complete: %s', video_name)

    except Exception as exc:
        logger.error('Video build error: %s', exc)
        _update(status='error', message=f'Video build failed: {exc}')
