from __future__ import annotations
import asyncio
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from .. import config
from ..models.schemas import PreviewStatusResponse
from ..services.encoder import EncoderService, EncoderError

router = APIRouter(prefix="/api/preview")

_lock = threading.Lock()
_generating = False
_ready = False
_preview_path: Optional[Path] = None
_current_run_id: Optional[str] = None


def _reset():
    global _generating, _ready, _preview_path
    _generating = False
    _ready = False
    _preview_path = None


def _build_preview(frame_dir: Path, output_path: Path, fps: int, encoder: EncoderService):
    global _generating, _ready, _preview_path
    try:
        encoder.build_preview(frame_dir, output_path, fps)
        with _lock:
            _ready = True
            _preview_path = output_path
    except EncoderError as exc:
        with _lock:
            _ready = False
    finally:
        with _lock:
            _generating = False


@router.get("", status_code=202)
async def trigger_preview(request: Request):
    global _generating, _ready, _current_run_id

    state = request.app.state.state_manager
    run = state._current_run

    if run is None or run["frames_captured"] == 0:
        raise HTTPException(status_code=404, detail="No frames available for preview")

    with _lock:
        if _generating:
            return {"generating": True, "ready": False, "url": None}
        if _ready and _current_run_id == run["id"]:
            return {"generating": False, "ready": True, "url": "/api/preview/file"}

        _generating = True
        _ready = False
        _current_run_id = run["id"]

    config.PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    frame_dir = Path(run["frame_dir"])
    output_path = config.PREVIEWS_DIR / f"{run['id']}_preview.mp4"
    encoder = request.app.state.encoder

    loop = asyncio.get_event_loop()
    threading.Thread(
        target=_build_preview,
        args=(frame_dir, output_path, run["fps"], encoder),
        daemon=True,
    ).start()

    return {"generating": True, "ready": False, "url": None}


@router.get("/status", response_model=PreviewStatusResponse)
async def preview_status():
    with _lock:
        return PreviewStatusResponse(
            generating=_generating,
            ready=_ready,
            url="/api/preview/file" if _ready else None,
        )


@router.get("/file")
async def preview_file(request: Request):
    with _lock:
        path = _preview_path

    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Preview not ready")

    ttl = config.PREVIEW_TTL_SECONDS

    async def cleanup():
        await asyncio.sleep(ttl)
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        global _ready, _preview_path
        with _lock:
            _ready = False
            _preview_path = None

    asyncio.create_task(cleanup())
    return FileResponse(str(path), media_type="video/mp4")
