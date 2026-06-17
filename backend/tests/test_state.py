import asyncio
import threading
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import aiosqlite

from backend.services.state import StateManager, ConflictError
from backend import config


@pytest.mark.asyncio
async def test_initial_status_is_idle(state_manager):
    assert state_manager.status == "idle"


@pytest.mark.asyncio
async def test_start_transitions_to_capturing(state_manager, mock_camera, tmp_path):
    mock_camera.start_still_mode = MagicMock()
    mock_camera.stop_still_mode = MagicMock()
    mock_camera.capture_still = MagicMock(side_effect=lambda p: Path(p).touch())

    with patch("backend.services.state.asyncio.create_task"):
        run_id = await state_manager.start(interval=5, duration=1, fps=24, capture_width=640, capture_height=480)

    assert state_manager.status == "capturing"
    assert run_id is not None


@pytest.mark.asyncio
async def test_start_while_capturing_raises(state_manager, mock_camera):
    mock_camera.start_still_mode = MagicMock()
    mock_camera.stop_still_mode = MagicMock()
    mock_camera.capture_still = MagicMock(side_effect=lambda p: Path(p).touch())

    with patch("backend.services.state.asyncio.create_task"):
        await state_manager.start(interval=5, duration=1, fps=24, capture_width=640, capture_height=480)

    with pytest.raises(ConflictError):
        with patch("backend.services.state.asyncio.create_task"):
            await state_manager.start(interval=5, duration=1, fps=24, capture_width=640, capture_height=480)


@pytest.mark.asyncio
async def test_stop_while_idle_is_noop(state_manager):
    await state_manager.stop()
    assert state_manager.status == "idle"


@pytest.mark.asyncio
async def test_run_creates_db_record(state_manager, mock_camera):
    mock_camera.start_still_mode = MagicMock()
    mock_camera.stop_still_mode = MagicMock()
    mock_camera.capture_still = MagicMock(side_effect=lambda p: Path(p).touch())

    with patch("backend.services.state.asyncio.create_task"):
        run_id = await state_manager.start(interval=5, duration=1, fps=24, capture_width=640, capture_height=480)

    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM timelapse_runs WHERE id=?", (run_id,)) as cur:
            row = await cur.fetchone()

    assert row is not None
    assert row["status"] == "capturing"
    assert row["capture_width"] == 640
    assert row["capture_height"] == 480


@pytest.mark.asyncio
async def test_restart_after_done_is_allowed(state_manager, mock_camera, mock_ffmpeg):
    mock_camera.start_still_mode = MagicMock()
    mock_camera.stop_still_mode = MagicMock()
    mock_camera.capture_still = MagicMock(side_effect=lambda p: Path(p).touch())

    # Force state to "done"
    state_manager._current_run = {
        "id": "abc", "status": "done", "started_at": "2024-01-01", "completed_at": "2024-01-01",
        "interval_seconds": 5, "duration_minutes": 1, "fps": 24,
        "frames_captured": 10, "frames_total": 10, "frame_dir": str(config.FRAMES_DIR / "abc"),
        "video_id": "xyz", "error_message": None, "triggered_by": "manual",
        "capture_width": 640, "capture_height": 480,
    }

    with patch("backend.services.state.asyncio.create_task"):
        run_id = await state_manager.start(interval=5, duration=1, fps=24, capture_width=640, capture_height=480)

    assert state_manager.status == "capturing"


@pytest.mark.asyncio
async def test_restart_after_error_is_allowed(state_manager):
    state_manager._current_run = {
        "id": "abc", "status": "error",
        "started_at": "2024-01-01", "completed_at": "2024-01-01",
        "interval_seconds": 5, "duration_minutes": 1, "fps": 24,
        "frames_captured": 0, "frames_total": 10, "frame_dir": str(config.FRAMES_DIR / "abc"),
        "video_id": None, "error_message": "boom", "triggered_by": "manual",
        "capture_width": 640, "capture_height": 480,
    }

    with patch("backend.services.state.asyncio.create_task"):
        run_id = await state_manager.start(interval=5, duration=1, fps=24, capture_width=640, capture_height=480)

    assert state_manager.status == "capturing"
