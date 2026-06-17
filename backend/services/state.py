from __future__ import annotations
import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from .. import config
from ..models.schemas import TimelapsStatusResponse
from .capture import CaptureService, CaptureError
from .encoder import EncoderService, EncoderError

logger = logging.getLogger(__name__)


class ConflictError(Exception):
    pass


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


class StateManager:
    def __init__(self, camera, encoder: EncoderService, video_library):
        self._camera = camera
        self._encoder = encoder
        self._video_library = video_library
        self._lock = asyncio.Lock()
        self._stop_event = threading.Event()
        self._current_run: Optional[dict] = None
        self._capture_service: Optional[CaptureService] = None
        self._ws_queues: list[asyncio.Queue] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ── WebSocket subscription ─────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._ws_queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._ws_queues.remove(q)
        except ValueError:
            pass

    def _push(self, msg: dict) -> None:
        for q in list(self._ws_queues):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    def _push_threadsafe(self, msg: dict) -> None:
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._push, msg)

    # ── Public API ─────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        run = self._current_run
        return run["status"] if run else "idle"

    def get_status(self) -> TimelapsStatusResponse:
        run = self._current_run
        if run is None:
            return TimelapsStatusResponse(
                run_id=None, status="idle", captured=0, total=0,
                message="", video_id=None, started_at=None,
                capture_width=None, capture_height=None,
            )
        return TimelapsStatusResponse(
            run_id=run["id"],
            status=run["status"],
            captured=run["frames_captured"],
            total=run["frames_total"],
            message=run.get("error_message") or "",
            video_id=run.get("video_id"),
            started_at=run.get("started_at"),
            capture_width=run.get("capture_width"),
            capture_height=run.get("capture_height"),
        )

    async def start(
        self,
        interval: int,
        duration: int,
        fps: int,
        triggered_by: str = "manual",
        capture_width: int = 1920,
        capture_height: int = 1080,
    ) -> str:
        async with self._lock:
            if self._current_run and self._current_run["status"] in ("capturing", "building"):
                raise ConflictError(f"Cannot start: currently {self._current_run['status']}")

            run_id = str(uuid.uuid4())
            total = max(1, int(duration * 60 / interval))
            frame_dir = config.FRAMES_DIR / run_id

            self._current_run = {
                "id": run_id,
                "started_at": _utcnow(),
                "completed_at": None,
                "status": "capturing",
                "interval_seconds": interval,
                "duration_minutes": duration,
                "fps": fps,
                "frames_captured": 0,
                "frames_total": total,
                "frame_dir": str(frame_dir),
                "video_id": None,
                "error_message": None,
                "triggered_by": triggered_by,
                "capture_width": capture_width,
                "capture_height": capture_height,
            }
            self._stop_event.clear()
            self._capture_service = CaptureService(self._camera)

        await self._save_run()
        self._push({"event": "status", "data": {"status": "capturing", "captured": 0, "total": total}})
        asyncio.create_task(self._run_capture())
        return run_id

    async def stop(self) -> None:
        self._stop_event.set()

    # ── Internal ───────────────────────────────────────────────────────

    async def _run_capture(self) -> None:
        run = self._current_run
        frame_dir = Path(run["frame_dir"])

        # Start progress watcher
        watcher = asyncio.create_task(self._progress_watcher())

        try:
            await asyncio.to_thread(
                self._capture_service.start,
                run["id"],
                run["interval_seconds"],
                run["frames_total"],
                frame_dir,
                self._stop_event,
                run["capture_width"],
                run["capture_height"],
            )
        except CaptureError as exc:
            watcher.cancel()
            async with self._lock:
                run["status"] = "error"
                run["error_message"] = str(exc)
                run["completed_at"] = _utcnow()
                run["frames_captured"] = self._capture_service.captured_count
            await self._save_run()
            self._push({"event": "error", "data": {"message": str(exc)}})
            return
        finally:
            watcher.cancel()

        # Sync final count
        async with self._lock:
            run["frames_captured"] = self._capture_service.captured_count

        if self._stop_event.is_set() and run["frames_captured"] == 0:
            async with self._lock:
                run["status"] = "idle"
                run["completed_at"] = _utcnow()
            await self._save_run()
            self._push({"event": "status", "data": {"status": "idle", "captured": 0, "total": run["frames_total"]}})
            return

        if self._stop_event.is_set():
            async with self._lock:
                run["status"] = "cancelled"
                run["completed_at"] = _utcnow()
            await self._save_run()
            self._push({"event": "status", "data": {"status": "cancelled", "captured": run["frames_captured"], "total": run["frames_total"]}})
            return

        # Build video
        async with self._lock:
            run["status"] = "building"
        await self._save_run()
        self._push({"event": "status", "data": {"status": "building", "captured": run["frames_captured"], "total": run["frames_total"]}})

        try:
            tmp_path = config.DATA_DIR / f"tmp_{run['id']}.mp4"
            await asyncio.to_thread(
                self._encoder.build_video,
                frame_dir,
                tmp_path,
                run["fps"],
            )

            video = await self._video_library.register_video(
                tmp_path,
                run["id"],
                run["frames_captured"],
                run["fps"],
            )

            async with self._lock:
                run["status"] = "done"
                run["video_id"] = video.id
                run["completed_at"] = _utcnow()
            await self._save_run()
            self._push({"event": "done", "data": {"video_id": video.id, "filename": video.filename}})

        except (EncoderError, Exception) as exc:
            async with self._lock:
                run["status"] = "error"
                run["error_message"] = f"Encoding failed: {exc}"
                run["completed_at"] = _utcnow()
            await self._save_run()
            self._push({"event": "error", "data": {"message": run["error_message"]}})

    async def _progress_watcher(self) -> None:
        while True:
            await asyncio.sleep(2)
            run = self._current_run
            if not run or run["status"] != "capturing":
                break
            if self._capture_service:
                count = self._capture_service.captured_count
                async with self._lock:
                    run["frames_captured"] = count
                self._push({
                    "event": "status",
                    "data": {"status": "capturing", "captured": count, "total": run["frames_total"]},
                })

    async def _save_run(self) -> None:
        run = self._current_run
        if not run:
            return
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                """INSERT INTO timelapse_runs
                   (id, started_at, completed_at, status, interval_seconds, duration_minutes,
                    fps, frames_captured, frames_total, frame_dir, video_id, error_message,
                    triggered_by, capture_width, capture_height)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     completed_at=excluded.completed_at,
                     status=excluded.status,
                     frames_captured=excluded.frames_captured,
                     video_id=excluded.video_id,
                     error_message=excluded.error_message""",
                (
                    run["id"], run["started_at"], run["completed_at"], run["status"],
                    run["interval_seconds"], run["duration_minutes"], run["fps"],
                    run["frames_captured"], run["frames_total"], run["frame_dir"],
                    run["video_id"], run["error_message"], run["triggered_by"],
                    run["capture_width"], run["capture_height"],
                ),
            )
            await db.commit()
