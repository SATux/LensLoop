from __future__ import annotations
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from .. import config
from ..models.schemas import ScheduleCreateRequest, ScheduleResponse

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, state_manager):
        self._state = state_manager
        self._scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        self._scheduler.start()
        await self._load_jobs_from_db()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    # ── CRUD ───────────────────────────────────────────────────────────

    async def list_jobs(self) -> list[ScheduleResponse]:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM scheduled_jobs ORDER BY created_at DESC") as cur:
                rows = await cur.fetchall()
        return [_row_to_schedule(r) for r in rows]

    async def get_job(self, job_id: str) -> Optional[ScheduleResponse]:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM scheduled_jobs WHERE id=?", (job_id,)) as cur:
                row = await cur.fetchone()
        return _row_to_schedule(row) if row else None

    async def create_job(self, req: ScheduleCreateRequest) -> ScheduleResponse:
        if not croniter.is_valid(req.cron_expression):
            raise ValueError(f"Invalid cron expression: {req.cron_expression!r}")

        job_id = str(uuid.uuid4())
        now = _sastnow()
        trigger = CronTrigger.from_crontab(req.cron_expression)
        next_run = _next_fire(trigger)

        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                """INSERT INTO scheduled_jobs
                   (id, name, cron_expression, interval_seconds, duration_minutes, fps,
                    capture_width, capture_height, enabled, created_at, next_run_at)
                   VALUES (?,?,?,?,?,?,?,?,1,?,?)""",
                (job_id, req.name, req.cron_expression, req.interval, req.duration,
                 req.fps, req.capture_width, req.capture_height, now, next_run),
            )
            await db.commit()

        self._register(job_id, req.cron_expression, req.interval, req.duration,
                       req.fps, req.capture_width, req.capture_height)
        return (await self.get_job(job_id))

    async def update_job(self, job_id: str, req: ScheduleCreateRequest) -> ScheduleResponse:
        if not croniter.is_valid(req.cron_expression):
            raise ValueError(f"Invalid cron expression: {req.cron_expression!r}")

        trigger = CronTrigger.from_crontab(req.cron_expression)
        next_run = _next_fire(trigger)

        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                """UPDATE scheduled_jobs SET
                   name=?, cron_expression=?, interval_seconds=?, duration_minutes=?,
                   fps=?, capture_width=?, capture_height=?, next_run_at=?
                   WHERE id=?""",
                (req.name, req.cron_expression, req.interval, req.duration,
                 req.fps, req.capture_width, req.capture_height, next_run, job_id),
            )
            await db.commit()

        self._deregister(job_id)
        job = await self.get_job(job_id)
        if job and job.enabled:
            self._register(job_id, req.cron_expression, req.interval, req.duration,
                           req.fps, req.capture_width, req.capture_height)
        return job

    async def delete_job(self, job_id: str) -> None:
        self._deregister(job_id)
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
            await db.commit()

    async def set_enabled(self, job_id: str, enabled: bool) -> Optional[ScheduleResponse]:
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                "UPDATE scheduled_jobs SET enabled=? WHERE id=?", (1 if enabled else 0, job_id)
            )
            await db.commit()

        job = await self.get_job(job_id)
        if job is None:
            return None

        self._deregister(job_id)
        if enabled:
            self._register(job_id, job.cron_expression, job.interval, job.duration,
                           job.fps, job.capture_width, job.capture_height)
        return job

    async def trigger_now(self, job_id: str):
        job = await self.get_job(job_id)
        if job is None:
            return None
        return await self._run_job(job_id, job)

    # ── Internal ───────────────────────────────────────────────────────

    async def _load_jobs_from_db(self) -> None:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM scheduled_jobs WHERE enabled=1") as cur:
                rows = await cur.fetchall()
        for row in rows:
            self._register(
                row["id"], row["cron_expression"],
                row["interval_seconds"], row["duration_minutes"], row["fps"],
                row["capture_width"], row["capture_height"],
            )

    def _register(
        self, job_id: str, cron_expr: str,
        interval: int, duration: int, fps: int,
        width: int, height: int,
    ) -> None:
        self._deregister(job_id)
        trigger = CronTrigger.from_crontab(cron_expr)
        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            args=[job_id, None],
            id=job_id,
            replace_existing=True,
        )

    def _deregister(self, job_id: str) -> None:
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

    async def _run_job(self, job_id: str, job_obj=None):
        from .state import ConflictError
        job = job_obj or await self.get_job(job_id)
        if job is None:
            return None

        now = _sastnow()
        try:
            status = await self._state.start(
                interval=job.interval,
                duration=job.duration,
                fps=job.fps,
                triggered_by=job_id,
                capture_width=job.capture_width,
                capture_height=job.capture_height,
            )
        except ConflictError:
            logger.info("Scheduled job %s skipped: timelapse already running", job_id)
            async with aiosqlite.connect(config.DB_PATH) as db:
                await db.execute(
                    "UPDATE scheduled_jobs SET last_run_at=? WHERE id=?", (now, job_id)
                )
                await db.commit()
            return None

        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                "UPDATE scheduled_jobs SET last_run_at=? WHERE id=?", (now, job_id)
            )
            await db.commit()

        return self._state.get_status()


_SAST = timezone(timedelta(hours=2))


def _sastnow() -> str:
    return datetime.now(_SAST).replace(tzinfo=None).isoformat()


def _next_fire(trigger) -> Optional[str]:
    try:
        nxt = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
        return nxt.astimezone(_SAST).replace(tzinfo=None).isoformat() if nxt else None
    except Exception:
        return None


def _row_to_schedule(row) -> ScheduleResponse:
    return ScheduleResponse(
        id=row["id"],
        name=row["name"],
        cron_expression=row["cron_expression"],
        interval=row["interval_seconds"],
        duration=row["duration_minutes"],
        fps=row["fps"],
        capture_width=row["capture_width"],
        capture_height=row["capture_height"],
        enabled=bool(row["enabled"]),
        next_run_at=row["next_run_at"],
        last_run_at=row["last_run_at"],
    )
