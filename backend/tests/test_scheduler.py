import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.scheduler import SchedulerService
from backend.models.schemas import ScheduleCreateRequest
from backend.database import init_db


_VALID_REQ = ScheduleCreateRequest(
    name="Morning", cron_expression="0 6 * * *",
    interval=10, duration=30, fps=24,
    capture_width=1920, capture_height=1080,
)


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.start = AsyncMock(return_value="run-id")
    state.get_status = MagicMock(return_value=MagicMock(status="capturing"))
    return state


@pytest_asyncio.fixture
async def scheduler(mock_state):
    await init_db()
    svc = SchedulerService(mock_state)
    await svc.start()
    yield svc
    svc.stop()


@pytest.mark.asyncio
async def test_add_job_registers_with_apscheduler(scheduler):
    before = len(scheduler._scheduler.get_jobs())
    await scheduler.create_job(_VALID_REQ)
    assert len(scheduler._scheduler.get_jobs()) == before + 1


@pytest.mark.asyncio
async def test_remove_job_deregisters(scheduler):
    job = await scheduler.create_job(_VALID_REQ)
    before = len(scheduler._scheduler.get_jobs())
    await scheduler.delete_job(job.id)
    assert len(scheduler._scheduler.get_jobs()) == before - 1


@pytest.mark.asyncio
async def test_disabled_job_not_added_to_scheduler(scheduler):
    before = len(scheduler._scheduler.get_jobs())
    job = await scheduler.create_job(_VALID_REQ)
    await scheduler.set_enabled(job.id, False)
    assert len(scheduler._scheduler.get_jobs()) == before


@pytest.mark.asyncio
async def test_enable_job_registers_it(scheduler):
    job = await scheduler.create_job(_VALID_REQ)
    await scheduler.set_enabled(job.id, False)
    before = len(scheduler._scheduler.get_jobs())
    await scheduler.set_enabled(job.id, True)
    assert len(scheduler._scheduler.get_jobs()) == before + 1


@pytest.mark.asyncio
async def test_trigger_job_calls_state_manager_start(scheduler, mock_state):
    job = await scheduler.create_job(_VALID_REQ)
    await scheduler.trigger_now(job.id)
    mock_state.start.assert_called_once_with(
        interval=10, duration=30, fps=24,
        triggered_by=job.id,
        capture_width=1920, capture_height=1080,
    )


@pytest.mark.asyncio
async def test_trigger_job_skips_if_already_running(scheduler, mock_state):
    from backend.services.state import ConflictError
    mock_state.start.side_effect = ConflictError("Already running")
    job = await scheduler.create_job(_VALID_REQ)
    result = await scheduler.trigger_now(job.id)
    assert result is None


@pytest.mark.asyncio
async def test_invalid_cron_raises_on_add(scheduler):
    req = ScheduleCreateRequest(
        name="Bad", cron_expression="not valid",
        interval=5, duration=10, fps=24,
        capture_width=640, capture_height=480,
    )
    with pytest.raises(ValueError):
        await scheduler.create_job(req)


@pytest.mark.asyncio
async def test_startup_loads_jobs_from_db(mock_state):
    await init_db()
    # Create 2 jobs in DB, then restart scheduler and check they load
    svc = SchedulerService(mock_state)
    await svc.start()
    await svc.create_job(_VALID_REQ)
    req2 = ScheduleCreateRequest(
        name="Evening", cron_expression="0 20 * * *",
        interval=5, duration=10, fps=24,
        capture_width=640, capture_height=480,
    )
    await svc.create_job(req2)
    svc.stop()

    svc2 = SchedulerService(mock_state)
    await svc2.start()
    assert len(svc2._scheduler.get_jobs()) >= 2
    svc2.stop()
