from fastapi import APIRouter, HTTPException, Request, Response, status

from ..models.schemas import ScheduleCreateRequest, ScheduleResponse, TimelapsStatusResponse
from ..services.state import ConflictError

router = APIRouter(prefix="/api/schedule")


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(request: Request):
    return await request.app.state.scheduler.list_jobs()


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleCreateRequest, request: Request):
    try:
        return await request.app.state.scheduler.create_job(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{job_id}", response_model=ScheduleResponse)
async def get_schedule(job_id: str, request: Request):
    job = await request.app.state.scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return job


@router.put("/{job_id}", response_model=ScheduleResponse)
async def update_schedule(job_id: str, body: ScheduleCreateRequest, request: Request):
    job = await request.app.state.scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    try:
        return await request.app.state.scheduler.update_job(job_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{job_id}", status_code=204)
async def delete_schedule(job_id: str, request: Request):
    job = await request.app.state.scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await request.app.state.scheduler.delete_job(job_id)
    return Response(status_code=204)


@router.post("/{job_id}/enable", response_model=ScheduleResponse)
async def enable_schedule(job_id: str, request: Request):
    job = await request.app.state.scheduler.set_enabled(job_id, True)
    if job is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return job


@router.post("/{job_id}/disable", response_model=ScheduleResponse)
async def disable_schedule(job_id: str, request: Request):
    job = await request.app.state.scheduler.set_enabled(job_id, False)
    if job is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return job


@router.post("/{job_id}/run_now", status_code=status.HTTP_202_ACCEPTED)
async def run_now(job_id: str, request: Request):
    job = await request.app.state.scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    try:
        result = await request.app.state.scheduler.trigger_now(job_id)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=409, detail="Timelapse already running")
    return result
