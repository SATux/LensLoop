import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend import config


def _set_run(test_app, status="capturing", captured=5, total=12):
    state = test_app.app.state.state_manager
    state._current_run = {
        "id": "preview-run-id",
        "status": status,
        "frames_captured": captured,
        "frames_total": total,
        "frame_dir": str(config.FRAMES_DIR / "preview-run-id"),
        "fps": 24,
        "interval_seconds": 5, "duration_minutes": 1,
        "started_at": "2024-01-01T00:00:00",
        "completed_at": None,
        "video_id": None,
        "error_message": None,
        "triggered_by": "manual",
        "capture_width": 1920, "capture_height": 1080,
    }
    return state


@pytest.mark.asyncio
async def test_preview_status_no_frames_returns_not_started(test_app):
    resp = await test_app.get("/api/preview/status")
    assert resp.status_code == 200
    assert resp.json()["ready"] is False
    assert resp.json()["generating"] is False


@pytest.mark.asyncio
async def test_preview_generation_triggered(test_app, tmp_path):
    import backend.routers.preview as preview_mod
    preview_mod._reset()

    state = _set_run(test_app)
    frame_dir = Path(state._current_run["frame_dir"])
    frame_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 4):
        (frame_dir / f"frame_{i:06d}.jpg").write_bytes(b"\xff\xd8\xff\xd9")

    with patch("backend.routers.preview.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        resp = await test_app.get("/api/preview")

    assert resp.status_code == 202
    preview_mod._reset()


@pytest.mark.asyncio
async def test_second_preview_request_while_generating(test_app, tmp_path):
    import backend.routers.preview as preview_mod
    preview_mod._reset()
    preview_mod._generating = True

    _set_run(test_app)
    resp = await test_app.get("/api/preview")

    data = resp.json()
    assert data["generating"] is True
    assert data["ready"] is False
    preview_mod._reset()


@pytest.mark.asyncio
async def test_preview_file_returns_mp4(test_app, tmp_path):
    import backend.routers.preview as preview_mod
    preview_mod._reset()

    fake_mp4 = config.PREVIEWS_DIR / "preview-run-id_preview.mp4"
    config.PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    fake_mp4.write_bytes(b"fake mp4 preview content")

    preview_mod._ready = True
    preview_mod._preview_path = fake_mp4

    resp = await test_app.get("/api/preview/file")
    assert resp.status_code == 200
    assert "video/mp4" in resp.headers.get("content-type", "")
    preview_mod._reset()


@pytest.mark.asyncio
async def test_preview_does_not_delete_frames(test_app, sample_frames):
    import backend.routers.preview as preview_mod
    preview_mod._reset()

    state = _set_run(test_app)
    state._current_run["frame_dir"] = str(sample_frames)

    frames_before = list(sample_frames.glob("frame_*.jpg"))
    assert len(frames_before) == 5

    with patch("backend.routers.preview.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        await test_app.get("/api/preview")

    frames_after = list(sample_frames.glob("frame_*.jpg"))
    assert len(frames_after) == 5
    preview_mod._reset()
