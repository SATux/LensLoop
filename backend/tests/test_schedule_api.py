import pytest


_VALID_SCHEDULE = {
    "name": "Morning Timelapse",
    "cron_expression": "0 6 * * *",
    "interval": 10,
    "duration": 30,
    "fps": 24,
    "capture_width": 1920,
    "capture_height": 1080,
}


@pytest.mark.asyncio
async def test_create_schedule_returns_201(test_app):
    resp = await test_app.post("/api/schedule", json=_VALID_SCHEDULE)
    assert resp.status_code == 201
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_create_schedule_persists_to_db(test_app):
    await test_app.post("/api/schedule", json=_VALID_SCHEDULE)
    resp = await test_app.get("/api/schedule")
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_create_schedule_invalid_cron_returns_422(test_app):
    body = {**_VALID_SCHEDULE, "cron_expression": "not valid cron"}
    resp = await test_app.post("/api/schedule", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_schedule_list_empty(test_app):
    resp = await test_app.get("/api/schedule")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_schedule_changes_cron(test_app):
    create_resp = await test_app.post("/api/schedule", json=_VALID_SCHEDULE)
    job_id = create_resp.json()["id"]

    updated = {**_VALID_SCHEDULE, "cron_expression": "0 8 * * *"}
    resp = await test_app.put(f"/api/schedule/{job_id}", json=updated)
    assert resp.json()["cron_expression"] == "0 8 * * *"


@pytest.mark.asyncio
async def test_delete_schedule_removes_from_db(test_app):
    create_resp = await test_app.post("/api/schedule", json=_VALID_SCHEDULE)
    job_id = create_resp.json()["id"]

    await test_app.delete(f"/api/schedule/{job_id}")
    resp = await test_app.get("/api/schedule")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_enable_disable_toggle(test_app):
    create_resp = await test_app.post("/api/schedule", json=_VALID_SCHEDULE)
    job_id = create_resp.json()["id"]

    resp = await test_app.post(f"/api/schedule/{job_id}/disable")
    assert resp.json()["enabled"] is False

    resp = await test_app.post(f"/api/schedule/{job_id}/enable")
    assert resp.json()["enabled"] is True


@pytest.mark.asyncio
async def test_run_now_while_running_returns_409(test_app):
    from unittest.mock import AsyncMock
    create_resp = await test_app.post("/api/schedule", json=_VALID_SCHEDULE)
    job_id = create_resp.json()["id"]

    from backend.services.state import ConflictError
    sched = test_app.app.state.scheduler
    sched._state.start = AsyncMock(side_effect=ConflictError("Already running"))

    resp = await test_app.post(f"/api/schedule/{job_id}/run_now")
    assert resp.status_code == 409
