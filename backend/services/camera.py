from __future__ import annotations
import io
import logging
import threading
import time
from typing import Optional

from ..models.schemas import CaptureMode
from .. import config

logger = logging.getLogger(__name__)


class FrameBuffer(io.BufferedIOBase):
    def __init__(self):
        self.frame: Optional[bytes] = None
        self.ready = threading.Condition()

    def write(self, data: bytes) -> int:
        with self.ready:
            self.frame = data
            self.ready.notify_all()
        return len(data)


def _make_capture_mode(mode: dict, native_w: int, native_h: int) -> CaptureMode:
    raw_size = mode["size"]
    # picamera2 may return a Size object or a plain tuple
    try:
        w, h = int(raw_size[0]), int(raw_size[1])
    except TypeError:
        w, h = int(raw_size.width), int(raw_size.height)

    bit_depth = mode.get("bit_depth", 8)

    raw_crop = mode.get("crop_limits", (0, 0, native_w, native_h))
    try:
        crop = (int(raw_crop[0]), int(raw_crop[1]), int(raw_crop[2]), int(raw_crop[3]))
    except Exception:
        crop = (0, 0, native_w, native_h)

    full_fov = (crop[0] == 0 and crop[1] == 0 and crop[2] == native_w and crop[3] == native_h)
    mp = round(w * h / 1_000_000, 1)

    # picamera2 uses 'fps' (float); older builds may use 'fps_range' tuple
    fps_val = mode.get("fps") or mode.get("fps_range")
    if isinstance(fps_val, (list, tuple)):
        max_fps = float(fps_val[-1])
    elif fps_val is not None:
        max_fps = float(fps_val)
    else:
        max_fps = 30.0

    if (w, h) == (native_w, native_h):
        label = "Full res"
        description = "Full field of view, native resolution"
    elif full_fov:
        label = "Half-res"
        description = "Full field of view, 2×2 binned — good for low light"
    elif (w, h) == (1920, 1080):
        label = "1080p"
        description = "HD center crop"
    elif (w, h) == (640, 480):
        label = "Preview"
        description = "Small center crop, fastest capture"
    else:
        label = f"{w}×{h}"
        description = "Center crop"

    return CaptureMode(
        width=w,
        height=h,
        megapixels=mp,
        max_fps=max_fps,
        bit_depth=bit_depth,
        full_fov=full_fov,
        label=label,
        description=description,
    )


class CameraService:
    def __init__(self):
        self._cam = None
        self._lock = threading.Lock()
        self.available = False
        self.camera_model: str = "unknown"
        self.capture_modes: list[CaptureMode] = []
        self.frame_buffer = FrameBuffer()
        self._mode = "stopped"  # "stream" | "still" | "stopped"

    def start_stream(self) -> None:
        with self._lock:
            try:
                from picamera2 import Picamera2
                from picamera2.encoders import MJPEGEncoder
                from picamera2.outputs import FileOutput

                self._cam = Picamera2()

                # Read capabilities BEFORE configure/start_recording — calling
                # sensor_modes after recording begins triggers generateConfiguration()
                # on the active camera, which raises in some libcamera versions.
                self._populate_capabilities()

                cfg = self._cam.create_video_configuration(
                    main={"size": (config.CAM_WIDTH, config.CAM_HEIGHT)}
                )
                self._cam.configure(cfg)
                self._cam.start_recording(MJPEGEncoder(), FileOutput(self.frame_buffer))
                self.available = True
                self._mode = "stream"
                logger.info("Camera streaming at %dx%d", config.CAM_WIDTH, config.CAM_HEIGHT)
            except Exception as exc:
                logger.warning("Camera unavailable: %s", exc)
                self.available = False

    def _populate_capabilities(self) -> None:
        if self._cam is None:
            return
        try:
            props = self._cam.camera_properties
            self.camera_model = props.get("Model", "unknown")
            native_w, native_h = props.get("PixelArraySize", (0, 0))

            raw_modes = self._cam.sensor_modes
            seen: dict[tuple, dict] = {}
            for mode in raw_modes:
                raw_size = mode["size"]
                try:
                    size = (int(raw_size[0]), int(raw_size[1]))
                except TypeError:
                    size = (int(raw_size.width), int(raw_size.height))
                bd = mode.get("bit_depth", 8)
                if size not in seen or bd > seen[size].get("bit_depth", 0):
                    seen[size] = {**mode, "size": size}  # normalise size to plain tuple

            modes = [_make_capture_mode(m, native_w, native_h) for m in seen.values()]
            modes.sort(key=lambda m: m.width * m.height)
            self.capture_modes = modes
        except Exception as exc:
            logger.warning("Could not populate camera capabilities: %s", exc)

    def stop_stream(self) -> None:
        with self._lock:
            if self._cam is not None and self._mode == "stream":
                try:
                    self._cam.stop_recording()
                    self._cam.close()
                except Exception:
                    pass
                self._cam = None
            self.available = False
            self._mode = "stopped"

    def start_still_mode(self, width: int, height: int) -> None:
        with self._lock:
            if self._mode == "stream" and self._cam is not None:
                try:
                    self._cam.stop_recording()
                    self._cam.close()
                except Exception:
                    pass
                self._cam = None
                self.available = False
                self._mode = "stopped"

            time.sleep(0.5)

            try:
                from picamera2 import Picamera2
                self._cam = Picamera2()
                cfg = self._cam.create_still_configuration(main={"size": (width, height)})
                self._cam.configure(cfg)
                self._cam.start()
                self._mode = "still"
                logger.info("Camera in still mode at %dx%d", width, height)
            except Exception as exc:
                logger.error("Failed to start still mode: %s", exc)
                raise

    def stop_still_mode(self) -> None:
        with self._lock:
            if self._cam is not None and self._mode == "still":
                try:
                    self._cam.close()
                except Exception:
                    pass
                self._cam = None
            self._mode = "stopped"

        time.sleep(0.5)
        self.start_stream()

    def capture_still(self, path: str) -> None:
        if self._mode != "still" or self._cam is None:
            raise RuntimeError("Camera not in still mode")
        self._cam.capture_file(path)

    @staticmethod
    def global_info() -> dict:
        try:
            from picamera2 import Picamera2
            info = Picamera2.global_camera_info()
            if info:
                return {"model": info[0].get("Model", "unknown"), "available": True}
        except Exception:
            pass
        return {"model": "unknown", "available": False}
