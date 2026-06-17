import aiosqlite
from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS timelapse_runs (
    id TEXT PRIMARY KEY,
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    interval_seconds INTEGER,
    duration_minutes INTEGER,
    fps INTEGER,
    frames_captured INTEGER DEFAULT 0,
    frames_total INTEGER,
    frame_dir TEXT,
    video_id TEXT,
    error_message TEXT,
    triggered_by TEXT,
    capture_width INTEGER,
    capture_height INTEGER
);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    created_at TEXT NOT NULL,
    size_bytes INTEGER,
    duration_seconds REAL,
    frame_count INTEGER,
    fps INTEGER,
    width INTEGER,
    height INTEGER,
    run_id TEXT
);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    interval_seconds INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL,
    fps INTEGER NOT NULL,
    capture_width INTEGER NOT NULL,
    capture_height INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT
);
"""


async def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
        # Mark any interrupted runs as error
        await db.execute(
            "UPDATE timelapse_runs SET status='error', error_message='Server restarted during run' "
            "WHERE status IN ('capturing', 'building')"
        )
        await db.commit()


async def get_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
