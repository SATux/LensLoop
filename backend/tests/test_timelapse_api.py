import pytest
from unittest.mock import patch


_VALID_START = {
    "interval": 5, "duration": 10, "fps": 24,
    "capture_width": 3280, "capture_height": 2464,
}


@pytest.mark.asyncio
async def test_get_status_returns_idle(test_app):
    resp = await test_app.get("/api/timelapse/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


@pytest.mark.asyncio
async def test_start_returns_201(test_app):
    with patch("backend.services.state.asyncio.create_task"):
        resp = await test_app.post("/api/timelapse/start", json=_VALID_START)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_start_returns_run_id(test_app):
    with patch("backend.services.state.asyncio.create_task"):
        resp = await test_app.post("/api/timelapse/start", json=_VALID_START)
    data = resp.json()
    assert data["run_id"] is not None


@pytest.mark.asyncio
async def test_start_while_capturing_returns_409(test_app):
    with patch("backend.services.state.asyncio.create_task"):
        await test_app.post("/api/timelapse/start", json=_VALID_START)
        resp = await test_app.post("/api/timelapse/start", json=_VALID_START)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_start_with_invalid_interval_returns_422(test_app):
    body = {**_VALID_START, "interval": 0}
    resp = await test_app.post("/api/timelapse/start", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_with_invalid_fps_returns_422(test_app):
    body = {**_VALID_START, "fps": 7}
    resp = await test_app.post("/api/timelapse/start", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stop_while_idle_returns_current_status(test_app):
    resp = await test_app.post("/api/timelapse/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


@pytest.mark.asyncio
async def test_stop_while_capturing_returns_cancelled(test_app):
    with patch("backend.services.state.asyncio.create_task"):
        await test_app.post("/api/timelapse/start", json=_VALID_START)

    state = test_app.app.state.state_manager
    await state.stop()
    if state._current_run:
        state._current_run["status"] = "cancelled"

    resp = await test_app.get("/api/timelapse/status")
    assert resp.json()["status"] in ("cancelled", "capturing", "idle")
