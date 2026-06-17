from fastapi import APIRouter, HTTPException, Request, status

from ..models.schemas import TimelapsStartRequest, TimelapsStatusResponse
from ..services.state import ConflictError

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
