import pytest
from pathlib import Path

from backend import config


async def _seed_video(test_app, tmp_path) -> dict:
    """Insert a fake video record and return its data."""
    import aiosqlite
    from datetime import datetime
    vid_id = "test-video-id"
    filename = f"{vid_id}.mp4"
    dest = config.VIDEOS_DIR / filename
    dest.write_bytes(b"fake video content for testing range requests and streaming")

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO videos (id, filename, created_at, size_bytes, duration_seconds, frame_count, fps, width, height, run_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (vid_id, filename, "2024-01-01T00:00:00", dest.stat().st_size, 5.0, 10, 24, 1920, 1080, "run-1"),
        )
        await db.commit()
    return {"id": vid_id, "filename": filename}


@pytest.mark.asyncio
async def test_list_videos_empty(test_app):
    resp = await test_app.get("/api/videos")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_videos_returns_metadata(test_app, tmp_path):
    await _seed_video(test_app, tmp_path)
    resp = await test_app.get("/api/videos")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["fps"] == 24
    assert data[0]["width"] == 1920


@pytest.mark.asyncio
async def test_get_single_video_metadata(test_app, tmp_path):
    v = await _seed_video(test_app, tmp_path)
    resp = await test_app.get(f"/api/videos/{v['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == v["id"]


@pytest.mark.asyncio
async def test_get_unknown_video_returns_404(test_app):
    resp = await test_app.get("/api/videos/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_video_returns_204(test_app, tmp_path):
    v = await _seed_video(test_app, tmp_path)
    resp = await test_app.delete(f"/api/videos/{v['id']}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_unknown_video_returns_404(test_app):
    resp = await test_app.delete("/api/videos/not-found")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_video_file_endpoint_streams_bytes(test_app, tmp_path):
    v = await _seed_video(test_app, tmp_path)
    resp = await test_app.get(f"/api/videos/{v['id']}/file")
    assert resp.status_code == 200
    assert "video/mp4" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_video_file_supports_range_request(test_app, tmp_path):
    v = await _seed_video(test_app, tmp_path)
    resp = await test_app.get(
        f"/api/videos/{v['id']}/file",
        headers={"Range": "bytes=0-9"},
    )
    assert resp.status_code == 206
    assert "content-range" in resp.headers
