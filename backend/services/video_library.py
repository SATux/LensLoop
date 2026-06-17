from __future__ import annotations
import logging
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from .. import config
from ..models.schemas import VideoResponse
from .encoder import EncoderService

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    pass


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


class VideoLibrary:
    def __init__(self, encoder: EncoderService):
        self._encoder = encoder
        config.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        config.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    async def list_videos(self) -> list[VideoResponse]:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM videos ORDER BY created_at DESC"
            ) as cur:
                rows = await cur.fetchall()
        return [_row_to_video(r) for r in rows]

    async def get_video(self, video_id: str) -> Optional[VideoResponse]:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM videos WHERE id=?", (video_id,)) as cur:
                row = await cur.fetchone()
        return _row_to_video(row) if row else None

    async def register_video(
        self,
        tmp_path: Path,
        run_id: str,
        frame_count: int,
        fps: int,
    ) -> VideoResponse:
        video_id = str(uuid.uuid4())
        now = _utcnow()

        # Build a human-readable filename from the current SAST datetime (UTC+2, no DST)
        _SAST = timezone(timedelta(hours=2))
        ts = datetime.now(_SAST).strftime("%Y%m%d_%H%M%S")
        filename = f"timelapse_{ts}.mp4"
        # Avoid collision if two runs finish in the same second
        dest = config.VIDEOS_DIR / filename
        if dest.exists():
            filename = f"timelapse_{ts}_{video_id[:6]}.mp4"
            dest = config.VIDEOS_DIR / filename

        shutil.move(str(tmp_path), str(dest))

        meta = self._encoder.get_video_metadata(dest)
        size_bytes = dest.stat().st_size

        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                """INSERT INTO videos
                   (id, filename, created_at, size_bytes, duration_seconds,
                    frame_count, fps, width, height, run_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    video_id, filename, now, size_bytes,
                    meta.duration, frame_count, fps,
                    meta.width, meta.height, run_id,
                ),
            )
            await db.execute(
                "UPDATE timelapse_runs SET video_id=? WHERE id=?", (video_id, run_id)
            )
            await db.commit()

        # Delete source frames
        frame_dir = config.FRAMES_DIR / run_id
        if frame_dir.exists():
            shutil.rmtree(str(frame_dir), ignore_errors=True)

        return VideoResponse(
            id=video_id,
            filename=filename,
            created_at=now,
            size_bytes=size_bytes,
            duration_seconds=meta.duration,
            frame_count=frame_count,
            fps=fps,
            width=meta.width,
            height=meta.height,
            run_id=run_id,
        )

    async def delete_video(self, video_id: str) -> None:
        video = await self.get_video(video_id)
        if video is None:
            raise NotFoundError(f"Video {video_id} not found")

        path = config.VIDEOS_DIR / video.filename
        path.unlink(missing_ok=True)

        thumb = config.THUMBNAILS_DIR / f"{video_id}.jpg"
        thumb.unlink(missing_ok=True)

        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("DELETE FROM videos WHERE id=?", (video_id,))
            await db.commit()

    def thumbnail_path(self, video_id: str, video_filename: str) -> Path:
        thumb = config.THUMBNAILS_DIR / f"{video_id}.jpg"
        if not thumb.exists():
            video_path = config.VIDEOS_DIR / video_filename
            self._encoder.extract_thumbnail(video_path, thumb)
        return thumb


def _row_to_video(row) -> VideoResponse:
    return VideoResponse(
        id=row["id"],
        filename=row["filename"],
        created_at=row["created_at"],
        size_bytes=row["size_bytes"] or 0,
        duration_seconds=row["duration_seconds"] or 0.0,
        frame_count=row["frame_count"] or 0,
        fps=row["fps"] or 0,
        width=row["width"] or 0,
        height=row["height"] or 0,
        run_id=row["run_id"],
    )
