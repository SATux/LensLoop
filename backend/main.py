from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .database import init_db
from .services.camera import CameraService
from .services.encoder import EncoderService
from .services.state import StateManager
from .services.scheduler import SchedulerService
from .services.video_library import VideoLibrary
from .routers import stream, camera, timelapse, preview, videos, schedule, ws

logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="[%(levelname)s] %(asctime)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    config.PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    config.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    config.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    await init_db()

    cam = CameraService()
    cam.start_stream()

    enc = EncoderService()
    lib = VideoLibrary(enc)
    state = StateManager(cam, enc, lib)
    state.set_loop(asyncio.get_event_loop())

    sched = SchedulerService(state)
    await sched.start()

    app.state.camera = cam
    app.state.encoder = enc
    app.state.video_library = lib
    app.state.state_manager = state
    app.state.scheduler = sched

    logger.info("LensLoop backend started on %s:%s", config.HOST, config.PORT)
    yield

    sched.stop()
    cam.stop_stream()
    logger.info("LensLoop backend shut down")


app = FastAPI(title="LensLoop", lifespan=lifespan)

app.include_router(stream.router)
app.include_router(camera.router)
app.include_router(timelapse.router)
app.include_router(preview.router)
app.include_router(videos.router)
app.include_router(schedule.router)
app.include_router(ws.router)

_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="spa")


def serve():
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL,
    )
