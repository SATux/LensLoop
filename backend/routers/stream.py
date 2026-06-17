import asyncio
import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..models.schemas import StreamQualityRequest

router = APIRouter()

_PLACEHOLDER = Path(__file__).parent.parent.parent / "static" / "placeholder.jpg"


def _placeholder_bytes() -> bytes:
    if _PLACEHOLDER.exists():
        return _PLACEHOLDER.read_bytes()
    # 1×1 white JPEG fallback
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
        b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
        b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1edL\t\r\x83\xff\xd9"
    )


async def mjpeg_stream(camera):
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\n"

    if camera.available:
        while True:
            with camera.frame_buffer.ready:
                camera.frame_buffer.ready.wait(timeout=5.0)
                frame = camera.frame_buffer.frame
            if frame is None:
                await asyncio.sleep(0.05)
                continue
            yield (
                boundary
                + b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                + frame + b"\r\n"
            )
            await asyncio.sleep(0)
    else:
        frame = _placeholder_bytes()
        header = (
            boundary
            + b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
            + frame + b"\r\n"
        )
        while True:
            yield header
            await asyncio.sleep(1.0)


@router.get("/api/stream")
async def stream(request: Request):
    camera = request.app.state.camera
    return StreamingResponse(
        mjpeg_stream(camera),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/api/stream/quality")
async def get_stream_quality(request: Request):
    camera = request.app.state.camera
    return {"width": camera.stream_width, "height": camera.stream_height}


@router.post("/api/stream/quality")
async def set_stream_quality(body: StreamQualityRequest, request: Request):
    camera = request.app.state.camera
    if camera._mode not in ("stream", "stopped"):
        raise HTTPException(status_code=409, detail="Camera busy — cannot change quality now")
    valid = {(m.width, m.height) for m in camera.capture_modes}
    if valid and (body.width, body.height) not in valid:
        raise HTTPException(status_code=400, detail=f"Resolution {body.width}×{body.height} not supported")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, camera.set_stream_quality, body.width, body.height)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"width": camera.stream_width, "height": camera.stream_height}


@router.get("/api/debug/level")
async def get_log_level():
    level = logging.getLogger().level
    return {"level": logging.getLevelName(level)}


@router.post("/api/debug/level")
async def set_log_level(request: Request):
    body = await request.json()
    level_name = body.get("level", "INFO").upper()
    numeric = getattr(logging, level_name, None)
    if not isinstance(numeric, int):
        raise HTTPException(status_code=400, detail=f"Unknown log level: {level_name}")
    logging.getLogger().setLevel(numeric)
    # Also set picamera2 and our backend loggers
    for name in ("backend.services.camera", "picamera2", "picamera2.picamera2"):
        logging.getLogger(name).setLevel(numeric)
    return {"level": level_name}
