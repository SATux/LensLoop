# LensLoop

**GitHub:** https://github.com/SATux/LensLoop

Pi camera suite built on FastAPI + React 18 + Vite. Streams live MJPEG video, captures timelapse sequences, and assembles them into MP4s — all from a dark-mode web UI.

## Features

- **Live stream** — real-time MJPEG preview via WebSocket-backed player
- **Timelapse capture** — configurable interval, duration, resolution, and FPS; real-time progress via WebSocket
- **Scheduler** — cron-based recurring captures stored in SQLite, displayed in SAST (UTC+2)
- **Video library** — browse, stream (range requests), preview, and delete finished timelapses
- **Camera capabilities** — auto-detected sensor modes with megapixels, max FPS, and field-of-view info

## Requirements

```bash
sudo apt install python3-picamera2 ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
# node/npm — install via nvm or: sudo apt install nodejs npm
```

## Setup

```bash
# picamera2 is a system package — share it into the venv
uv venv --python /usr/bin/python3 --system-site-packages
uv sync
```

## Running

```bash
./start.sh
```

`start.sh` builds the React frontend if the dist is missing or stale, then starts uvicorn. Open `http://<pi-ip>:8000` in a browser.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | HTTP port |
| `HOST` | `0.0.0.0` | Bind address |
| `DATA_DIR` | `./data` | Root for frames, videos, DB |
| `CAM_WIDTH` | `1280` | Stream preview width |
| `CAM_HEIGHT` | `720` | Stream preview height |
| `LOG_LEVEL` | `info` | uvicorn log level |

### Entry point (without start.sh)

```bash
uv run serve
# or
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Project Structure

```
backend/
  main.py               # FastAPI app, lifespan, static SPA mount
  config.py             # Env-var config, derived paths
  database.py           # aiosqlite schema init
  models/schemas.py     # Pydantic schemas and dataclasses
  services/
    camera.py           # CameraService — MJPEG stream, still mode, capability discovery
    capture.py          # CaptureService — blocking frame loop (asyncio.to_thread)
    encoder.py          # EncoderService — ffmpeg/ffprobe wrapper
    state.py            # StateManager — state machine, asyncio.Lock, WS pub/sub
    scheduler.py        # SchedulerService — APScheduler + SQLite job store
    video_library.py    # VideoLibrary — file management + DB
  routers/              # FastAPI routers: stream, camera, timelapse, preview, videos, schedule, ws
  tests/                # pytest-asyncio test suite (74 tests)
frontend/
  src/pages/            # Dashboard, LiveStream, Capture, Schedule, Library
  src/components/       # Sidebar, TopBar, VideoPlayer, QualitySelector, etc.
  src/hooks/            # useStatus (WS), useVideos, useCapabilities
data/                   # Runtime data — gitignored
  frames/<run_id>/      # Captured JPEGs (deleted after video assembly)
  videos/               # Finished MP4s, named timelapse_YYYYMMDD_HHMMSS.mp4 (SAST)
  previews/             # Short preview clips
  thumbnails/           # Video poster frames
  timelapse.db          # SQLite: runs, videos, scheduled_jobs
LensLoop.png            # Wordmark logo (source)
start.sh                # Build frontend + start server
pyproject.toml
```

## API Overview

| Route | Method | Description |
|-------|--------|-------------|
| `/api/camera/info` | GET | Camera model and availability |
| `/api/camera/capabilities` | GET | Sensor modes (resolution, FPS, FOV) |
| `/api/stream` | GET | Raw MJPEG stream |
| `/api/timelapse/status` | GET | Current capture state |
| `/api/timelapse/start` | POST | Start capture |
| `/api/timelapse/stop` | POST | Abort capture |
| `/api/timelapse/build` | POST | Assemble frames → MP4 |
| `/api/preview/{run_id}` | GET | Short preview clip (202 while generating) |
| `/api/videos` | GET | List finished videos |
| `/api/videos/{id}` | GET | Stream video (range requests supported) |
| `/api/videos/{id}` | DELETE | Delete video + frames |
| `/api/schedule` | GET / POST | List / create scheduled jobs |
| `/api/schedule/{id}` | GET / PUT / DELETE | Get / update / delete job |
| `/api/schedule/{id}/enable` | PATCH | Enable or disable job |
| `/api/schedule/{id}/trigger` | POST | Run job immediately |
| `/ws/status` | WS | Real-time capture progress |

## Notes

- **Python**: must use `/usr/bin/python3` (system 3.11 with picamera2). Linuxbrew Python does not have picamera2.
- **Camera access**: only one process can hold the camera at a time. The server automatically stops the MJPEG stream before timelapse capture and restarts it when done.
- **Timestamps**: all scheduler and video timestamps are displayed in SAST (UTC+2, no DST).
- **Video filenames**: `timelapse_YYYYMMDD_HHMMSS.mp4` using SAST time; DB IDs remain UUIDs.
- **Tests**: `uv run pytest backend/tests/ -v`
