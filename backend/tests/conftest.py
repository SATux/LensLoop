from __future__ import annotations
import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Point DATA_DIR to a temp dir before any backend imports
_tmpdir = tempfile.mkdtemp()
os.environ.setdefault("DATA_DIR", _tmpdir)


@pytest.fixture(autouse=True)
def _reset_data_dir(tmp_path):
    """Give each test a clean isolated data directory."""
    import backend.config as config
    config.DATA_DIR = tmp_path
    config.FRAMES_DIR = tmp_path / "frames"
    config.PREVIEWS_DIR = tmp_path / "previews"
    config.VIDEOS_DIR = tmp_path / "videos"
    config.THUMBNAILS_DIR = tmp_path / "thumbnails"
    config.DB_PATH = tmp_path / "timelapse.db"
    for d in [config.FRAMES_DIR, config.PREVIEWS_DIR, config.VIDEOS_DIR, config.THUMBNAILS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def mock_camera():
    cam = MagicMock()
    cam.available = True
    cam.camera_model = "imx219"
    from backend.services.camera import CaptureMode, FrameBuffer
    cam.capture_modes = [
        CaptureMode(640, 480, 0.3, 206, 8, False, "Preview", "Small center crop, fastest capture"),
        CaptureMode(1640, 1232, 2.0, 41, 10, True, "Half-res", "Full field of view, 2×2 binned — good for low light"),
        CaptureMode(1920, 1080, 2.1, 47, 10, False, "1080p", "HD center crop"),
        CaptureMode(3280, 2464, 8.1, 21, 10, True, "Full res", "Full field of view, native resolution"),
    ]
    cam.frame_buffer = FrameBuffer()
    cam.global_info = MagicMock(return_value={"model": "imx219", "available": True})
    cam.start_still_mode = MagicMock()
    cam.stop_still_mode = MagicMock()
    cam.capture_still = MagicMock()
    return cam


@pytest.fixture
def sample_frames(tmp_path) -> Path:
    """5 minimal 1×1 JPEG files in a frame directory."""
    frame_dir = tmp_path / "frames" / "test-run"
    frame_dir.mkdir(parents=True)
    # Minimal valid JPEG bytes (1×1 white pixel)
    jpeg = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD2,
        0x8A, 0x28, 0x03, 0xFF, 0xD9,
    ])
    for i in range(1, 6):
        (frame_dir / f"frame_{i:06d}.jpg").write_bytes(jpeg)
    return frame_dir


@pytest.fixture
def mock_ffmpeg(monkeypatch):
    import subprocess
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = b'{"streams":[{"codec_type":"video","width":640,"height":480,"duration":"5.0"}]}'
    mock.return_value.stderr = b''
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


@pytest_asyncio.fixture
async def test_app(mock_camera, tmp_path):
    from backend.main import app
    from backend.database import init_db
    from backend.services.encoder import EncoderService
    from backend.services.state import StateManager
    from backend.services.scheduler import SchedulerService
    from backend.services.video_library import VideoLibrary

    await init_db()
    enc = EncoderService()
    lib = VideoLibrary(enc)
    state = StateManager(mock_camera, enc, lib)
    state.set_loop(asyncio.get_event_loop())
    sched = SchedulerService(state)

    app.state.camera = mock_camera
    app.state.encoder = enc
    app.state.video_library = lib
    app.state.state_manager = state
    app.state.scheduler = sched

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.app = app  # expose for tests that need direct app state access
        yield client


@pytest_asyncio.fixture
async def state_manager(mock_camera, tmp_path, mock_ffmpeg):
    from backend.database import init_db
    from backend.services.encoder import EncoderService
    from backend.services.state import StateManager
    from backend.services.video_library import VideoLibrary

    await init_db()
    enc = EncoderService()
    lib = VideoLibrary(enc)
    sm = StateManager(mock_camera, enc, lib)
    sm.set_loop(asyncio.get_event_loop())
    return sm


@pytest_asyncio.fixture
async def video_library(tmp_path, mock_ffmpeg):
    from backend.database import init_db
    from backend.services.encoder import EncoderService
    from backend.services.video_library import VideoLibrary

    await init_db()
    enc = EncoderService()
    return VideoLibrary(enc)
