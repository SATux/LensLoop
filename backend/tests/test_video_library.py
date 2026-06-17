import shutil
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio

from backend import config
from backend.database import init_db
from backend.services.video_library import VideoLibrary, NotFoundError
from backend.services.encoder import EncoderService


@pytest_asyncio.fixture
async def lib(mock_ffmpeg):
    await init_db()
    enc = EncoderService()
    return VideoLibrary(enc)


async def _make_video(lib: VideoLibrary, frame_dir: Path) -> "VideoResponse":
    # Create a fake mp4 in a temp location
    tmp = config.DATA_DIR / "tmp_test.mp4"
    tmp.write_bytes(b"fake mp4 content")
    frame_dir.mkdir(parents=True, exist_ok=True)
    return await lib.register_video(tmp, "test-run-id", 5, 24)


@pytest.mark.asyncio
async def test_register_video_creates_db_record(lib, tmp_path, sample_frames):
    video = await _make_video(lib, sample_frames.parent)
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM videos WHERE id=?", (video.id,)) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert row["run_id"] == "test-run-id"


@pytest.mark.asyncio
async def test_register_video_copies_file_to_data_dir(lib, sample_frames):
    video = await _make_video(lib, sample_frames.parent)
    dest = config.VIDEOS_DIR / video.filename
    assert dest.exists()


@pytest.mark.asyncio
async def test_register_video_deletes_frame_dir(lib, sample_frames):
    frame_dir = sample_frames
    video = await _make_video(lib, frame_dir.parent)
    # frame_dir should be gone (it's the run dir inside frames/)
    run_dir = config.FRAMES_DIR / "test-run-id"
    # Either the run dir doesn't exist or was cleaned up
    # The library deletes config.FRAMES_DIR / run_id
    assert not run_dir.exists()


@pytest.mark.asyncio
async def test_list_videos_newest_first(lib, sample_frames):
    v1 = await _make_video(lib, config.FRAMES_DIR / "run1")
    import asyncio; await asyncio.sleep(0.01)
    # Create a second tmp mp4
    tmp2 = config.DATA_DIR / "tmp_test2.mp4"
    tmp2.write_bytes(b"fake mp4 2")
    (config.FRAMES_DIR / "run2").mkdir(parents=True, exist_ok=True)
    v2 = await lib.register_video(tmp2, "run2", 3, 24)

    videos = await lib.list_videos()
    assert videos[0].id == v2.id
    assert videos[1].id == v1.id


@pytest.mark.asyncio
async def test_get_video_returns_none_for_unknown_id(lib):
    result = await lib.get_video("nonexistent-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_delete_video_removes_file_and_db_record(lib, sample_frames):
    video = await _make_video(lib, sample_frames.parent)
    path = config.VIDEOS_DIR / video.filename

    await lib.delete_video(video.id)

    assert not path.exists()
    result = await lib.get_video(video.id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_video_not_found_raises(lib):
    with pytest.raises(NotFoundError):
        await lib.delete_video("does-not-exist")


@pytest.mark.asyncio
async def test_metadata_populated_from_ffprobe(lib, sample_frames, mock_ffmpeg):
    video = await _make_video(lib, sample_frames.parent)
    # mock_ffmpeg returns width=640, height=480, duration=5.0
    assert video.width == 640
    assert video.height == 480
    assert video.duration_seconds == pytest.approx(5.0)
