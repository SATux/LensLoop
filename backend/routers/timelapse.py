import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from ..models.schemas import TimelapsStartRequest, TimelapsStatusResponse
from ..services.state import ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timelapse")


@router.get("/status", response_model=TimelapsStatusResponse)
async def get_status(request: Request):
    return request.app.state.state_manager.get_status()


@router.post("/start", response_model=TimelapsStatusResponse, status_code=status.HTTP_201_CREATED)
async def start_timelapse(body: TimelapsStartRequest, request: Request):
    camera = request.app.state.camera
    state = request.app.state.state_manager

    # Validate capture resolution against camera capabilities
    if camera.capture_modes:
        valid = {(m.width, m.height) for m in camera.capture_modes}
        if (body.capture_width, body.capture_height) not in valid:
            sizes = ", ".join(f"{w}×{h}" for w, h in sorted(valid))
            raise HTTPException(
                status_code=422,
                detail=f"Invalid capture size {body.capture_width}×{body.capture_height}. "
                       f"Valid sizes: {sizes}",
            )

    try:
        await state.start(
            interval=body.interval,
            duration=body.duration,
            fps=body.fps,
            triggered_by="manual",
            capture_width=body.capture_width,
            capture_height=body.capture_height,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return state.get_status()


@router.post("/stop", response_model=TimelapsStatusResponse)
async def stop_timelapse(request: Request):
    state = request.app.state.state_manager
    await state.stop()
    return state.get_status()


@router.get("/latest-frame")
async def latest_frame(request: Request, n: int = 0):
    state = request.app.state.state_manager
    run = state._current_run

    if run is None:
        logger.info("latest-frame n=%d: no current run", n)
        raise HTTPException(status_code=404, detail="No active capture")

    run_id = run["id"]
    frames_captured = run["frames_captured"]
    run_status = run["status"]
    frame_dir = Path(run["frame_dir"])
    dir_exists = frame_dir.exists()

    logger.info(
        "latest-frame n=%d | run=%s status=%s frames_captured=%d frame_dir=%s exists=%s",
        n, run_id[:8], run_status, frames_captured, frame_dir, dir_exists,
    )

    # Try the specific frame number the client asked for first
    if n > 0:
        p = frame_dir / f"frame_{n:06d}.jpg"
        if p.exists():
            return FileResponse(str(p), media_type="image/jpeg", headers={"Cache-Control": "no-store"})
        logger.info("latest-frame: frame_%06d.jpg not found", n)

    # Try the count the state manager knows about
    if frames_captured > 0:
        p = frame_dir / f"frame_{frames_captured:06d}.jpg"
        if p.exists():
            return FileResponse(str(p), media_type="image/jpeg", headers={"Cache-Control": "no-store"})
        logger.info("latest-frame: frame_%06d.jpg (state count) not found", frames_captured)

    # Last resort: newest file in the directory
    if dir_exists:
        frames = sorted(frame_dir.glob("frame_*.jpg"))
        logger.info("latest-frame: glob found %d files in %s", len(frames), frame_dir)
        if frames:
            return FileResponse(str(frames[-1]), media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    raise HTTPException(status_code=404, detail="No frames on disk yet")
