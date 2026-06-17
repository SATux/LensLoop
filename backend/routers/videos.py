from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from .. import config
from ..models.schemas import VideoResponse
from ..services.video_library import NotFoundError

router = APIRouter(prefix="/api/videos")


@router.get("", response_model=list[VideoResponse])
async def list_videos(request: Request):
    return await request.app.state.video_library.list_videos()


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, request: Request):
    video = await request.app.state.video_library.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/file")
async def video_file(video_id: str, request: Request):
    video = await request.app.state.video_library.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    path = config.VIDEOS_DIR / video.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing from disk")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        start, end = _parse_range(range_header, file_size)
        chunk_size = end - start + 1

        def iter_file():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = f.read(min(65536, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
            },
        )

    return FileResponse(str(path), media_type="video/mp4",
                        headers={"Accept-Ranges": "bytes"})


@router.delete("/{video_id}", status_code=204)
async def delete_video(video_id: str, request: Request):
    try:
        await request.app.state.video_library.delete_video(video_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    return Response(status_code=204)


@router.get("/{video_id}/thumbnail")
async def video_thumbnail(video_id: str, request: Request):
    video = await request.app.state.video_library.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        thumb = request.app.state.video_library.thumbnail_path(video_id, video.filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Thumbnail generation failed: {exc}")

    return FileResponse(str(thumb), media_type="image/jpeg")


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    try:
        _, range_spec = range_header.split("=", 1)
        start_str, end_str = range_spec.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        return start, end
    except Exception:
        return 0, file_size - 1
