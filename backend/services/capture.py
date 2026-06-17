from __future__ import annotations
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CaptureError(Exception):
    pass


class CaptureService:
    def __init__(self, camera):
        self._camera = camera
        self.captured_count: int = 0
        self._count_lock = threading.Lock()

    def start(
        self,
        run_id: str,
        interval: int,
        total_frames: int,
        frame_dir: Path,
        stop_event: threading.Event,
        width: int,
        height: int,
        on_frame: Optional[Callable[[int], None]] = None,
    ) -> None:
        frame_dir.mkdir(parents=True, exist_ok=True)
        with self._count_lock:
            self.captured_count = 0

        try:
            self._camera.start_still_mode(width, height)
        except Exception as exc:
            raise CaptureError(f"Failed to start still mode: {exc}") from exc

        try:
            seq = 0
            while seq < total_frames and not stop_event.is_set():
                seq += 1
                path = str(frame_dir / f"frame_{seq:06d}.jpg")
                try:
                    self._camera.capture_still(path)
                except Exception as exc:
                    raise CaptureError(f"Frame capture failed at seq {seq}: {exc}") from exc

                with self._count_lock:
                    self.captured_count = seq

                if on_frame:
                    try:
                        on_frame(seq)
                    except Exception:
                        pass

                if seq < total_frames and not stop_event.is_set():
                    stop_event.wait(timeout=interval)
        finally:
            try:
                self._camera.stop_still_mode()
            except Exception as exc:
                logger.warning("Error stopping still mode: %s", exc)
