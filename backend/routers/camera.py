from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/camera")


@router.get("/info")
async def camera_info(request: Request):
    camera = request.app.state.camera
    info = camera.global_info()
    return {"model": info["model"], "available": camera.available or info["available"]}


@router.get("/capabilities")
async def camera_capabilities(request: Request):
    camera = request.app.state.camera
    if not camera.available and not camera.capture_modes:
        raise HTTPException(status_code=503, detail="Camera not initialised")
    return {
        "model": camera.camera_model,
        "modes": [m.to_dict() for m in camera.capture_modes],
    }
