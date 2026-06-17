from __future__ import annotations
import io
import logging
import threading
import time
import traceback
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
        self.stream_width: int = config.CAM_WIDTH
        self.stream_height: int = config.CAM_HEIGHT

    def _start_mjpeg_recording(self, width: int, height: int) -> None:
        """Start MJPEG recording, falling back to software encoder if hardware rejects the resolution."""
        from picamera2.encoders import MJPEGEncoder
        from picamera2.outputs import FileOutput

        try:
            self._cam.start_recording(MJPEGEncoder(), FileOutput(self.frame_buffer))
            logger.debug("Hardware MJPEG encoder started at %dx%d", width, height)
        except (OSError, ProcessLookupError) as hw_exc:
            logger.warning(
                "Hardware MJPEG encoder rejected %dx%d (VIDIOC_STREAMON: %s) — "
                "falling back to LibavMjpegEncoder (software)",
                width, height, hw_exc,
            )
            try:
                from picamera2.encoders import LibavMjpegEncoder
            except ImportError:
                raise RuntimeError(
                    f"Hardware encoder can't handle {width}×{height} and "
                    "LibavMjpegEncoder (PyAV) is not installed"
                ) from hw_exc
            self._cam.start_recording(LibavMjpegEncoder(), FileOutput(self.frame_buffer))
            logger.info("Software MJPEG encoder (LibavMjpegEncoder) started at %dx%d", width, height)

    def start_stream(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        w = width or config.CAM_WIDTH
        h = height or config.CAM_HEIGHT
        with self._lock:
            try:
                from picamera2 import Picamera2

                self._cam = Picamera2()

                # Read capabilities BEFORE configure/start_recording — calling
                # sensor_modes after recording begins triggers generateConfiguration()
                # on the active camera, which raises in some libcamera versions.
                self._populate_capabilities()

                cfg = self._cam.create_video_configuration(main={"size": (w, h)})
                self._cam.configure(cfg)
                self._start_mjpeg_recording(w, h)
                self.available = True
                self._mode = "stream"
                self.stream_width = w
                self.stream_height = h
                logger.info("Camera streaming at %dx%d", w, h)
            except Exception as exc:
                logger.warning("Camera unavailable: %s", exc)
                self.available = False

    def set_stream_quality(self, width: int, height: int) -> None:
        with self._lock:
            logger.debug(
                "set_stream_quality: requested %dx%d | current mode=%s",
                width, height, self._mode,
            )

            if self._mode != "stream" or self._cam is None:
                logger.error("set_stream_quality called but camera not streaming (mode=%s)", self._mode)
                raise RuntimeError("Camera is not currently streaming")

            logger.debug("Calling stop_recording()...")
            try:
                self._cam.stop_recording()
                logger.debug("stop_recording() OK")
            except Exception as exc:
                logger.warning("stop_recording() raised (continuing): %s\n%s", exc, traceback.format_exc())

            logger.debug("Configuring at %dx%d...", width, height)
            try:
                cfg = self._cam.create_video_configuration(main={"size": (width, height)})
                self._cam.configure(cfg)
                logger.debug("configure() OK")
                self._start_mjpeg_recording(width, height)
                self.stream_width = width
                self.stream_height = height
                logger.info("Stream quality changed to %dx%d", width, height)
            except Exception as exc:
                logger.error(
                    "Failed to set stream quality: %s\n%s", exc, traceback.format_exc()
                )
                self.available = False
                self._mode = "stopped"
                raise

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
                except Exception:
                    pass
                try:
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
