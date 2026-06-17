from __future__ import annotations
import asyncio
import logging
import shutil
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from .. import config

router = APIRouter(prefix="/api/settings")
logger = logging.getLogger(__name__)


class SettingsUpdate(BaseModel):
    stream_width: Optional[int] = None
    stream_height: Optional[int] = None
    capture_interval: Optional[int] = None
    capture_duration: Optional[int] = None
    capture_fps: Optional[int] = None
    capture_width: Optional[int] = None
    capture_height: Optional[int] = None


@router.get("")
async def get_settings(request: Request):
    return request.app.state.settings.all()


@router.patch("")
async def update_settings(body: SettingsUpdate, request: Request):
    settings = request.app.state.settings
    camera = request.app.state.camera

    updates = body.model_dump(exclude_none=True)
    result = settings.update(updates)

    # If stream resolution changed, apply it immediately
    stream_changed = ("stream_width" in updates or "stream_height" in updates)
    if stream_changed and camera._mode == "stream":
        w = result["stream_width"]
        h = result["stream_height"]
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, camera.set_stream_quality, w, h)
        except Exception as exc:
            logger.warning("Could not apply new stream resolution immediately: %s", exc)

    return result


@router.delete("/data")
async def delete_all_data(request: Request):
    state = request.app.state.state_manager
    camera = request.app.state.camera

    # Abort any active capture first
    if state._current_run and state._current_run["status"] in ("capturing", "building"):
        await state.stop()
        await asyncio.sleep(1.0)

    # Wipe data directories (frames, videos, previews, thumbnails)
    for directory in (config.FRAMES_DIR, config.VIDEOS_DIR, config.PREVIEWS_DIR, config.THUMBNAILS_DIR):
        if directory.exists():
            shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)

    # Clear database tables
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM timelapse_runs")
        await db.execute("DELETE FROM videos")
        await db.commit()

    # Reset in-memory state
    state._current_run = None

    logger.info("All capture data deleted")
    return {"deleted": True}
