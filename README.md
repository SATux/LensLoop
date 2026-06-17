# LensLoop

**GitHub:** https://github.com/SATux/LensLoop

LensLoop is a self-hosted camera control and timelapse studio designed specifically for the **Raspberry Pi** with an official **Raspberry Pi Camera** (IMX219, IMX477, IMX708, and compatible modules). It runs entirely on the Pi — no cloud, no subscription — and is controlled from any browser on your local network.

Point your browser at the Pi's IP, watch a live MJPEG stream straight from the sensor, kick off a timelapse with one click, and come back later to find a finished MP4 waiting in the library. The scheduler lets you automate recurring shoots (sunrise every morning, plant time-lapse over a week), and the camera capability browser surfaces every sensor mode the hardware supports — resolution, megapixels, max frame rate, and whether you're getting the full field of view or a center crop.

Built on **FastAPI + React 18 + Vite**, backed by **picamera2** and **libcamera**.

## Features

- **Live stream** — real-time MJPEG preview with in-browser quality controls; automatically selects the hardware VideoCore encoder for supported resolutions and falls back to software encoding (LibavMjpegEncoder) for full-sensor modes
- **Timelapse capture** — configurable interval, duration, resolution, and FPS; real-time progress via WebSocket with live latest-frame preview as frames are captured
- **Capture preview** — the most recently captured frame appears on the Capture page and in the sidebar banner when you navigate away, so you can monitor a shoot from any page
- **Scheduler** — cron-based recurring captures stored in SQLite, displayed in SAST (UTC+2)
- **Video library** — browse, stream (range requests), preview, and delete finished timelapses
- **Camera capabilities** — auto-detected sensor modes with megapixels, max FPS, and field-of-view info
- **Settings** — persistent defaults for stream resolution and capture parameters (interval, duration, FPS, resolution); applied automatically on next session; includes a one-click "Delete all captures & videos" with confirmation
- **Runtime debug toggle** — switch server log level between INFO and DEBUG from the Live Stream page without restarting

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
| `CAM_WIDTH` | `1280` | Initial stream preview width (overridden by saved settings) |
| `CAM_HEIGHT` | `720` | Initial stream preview height (overridden by saved settings) |
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
    settings_store.py   # SettingsStore — JSON-backed persistent settings with defaults
    state.py            # StateManager — state machine, asyncio.Lock, WS pub/sub
    scheduler.py        # SchedulerService — APScheduler + SQLite job store
    video_library.py    # VideoLibrary — file management + DB
  routers/
    stream.py           # /api/stream, /api/stream/quality, /api/debug/level
    camera.py           # /api/camera/info, /api/camera/capabilities
    timelapse.py        # /api/timelapse/*, /api/timelapse/latest-frame
    preview.py          # /api/preview/*
    videos.py           # /api/videos/*
    schedule.py         # /api/schedule/*
    settings.py         # /api/settings, /api/settings/data
    ws.py               # /ws/status
  tests/                # pytest-asyncio test suite
frontend/
  src/pages/            # Dashboard, LiveStream, Capture, Schedule, Library, Settings
  src/components/       # Sidebar, TopBar, ActiveCaptureBanner, QualitySelector, etc.
  src/hooks/            # useStatus (WS), useVideos, useCapabilities
data/                   # Runtime data — gitignored
  frames/<run_id>/      # Captured JPEGs (deleted after video assembly)
  videos/               # Finished MP4s, named timelapse_YYYYMMDD_HHMMSS.mp4 (SAST)
  previews/             # Short preview clips
  thumbnails/           # Video poster frames
  timelapse.db          # SQLite: runs, videos, scheduled_jobs
  settings.json         # Persistent user settings
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
| `/api/stream/quality` | GET / POST | Get or change the live stream resolution |
| `/api/debug/level` | GET / POST | Get or set the server log level at runtime |
| `/api/timelapse/status` | GET | Current capture state |
| `/api/timelapse/start` | POST | Start capture |
| `/api/timelapse/stop` | POST | Abort capture |
| `/api/timelapse/build` | POST | Assemble frames → MP4 |
| `/api/timelapse/latest-frame` | GET | Latest captured JPEG (`?n=<frame_number>`) |
| `/api/preview/{run_id}` | GET | Short preview clip (202 while generating) |
| `/api/videos` | GET | List finished videos |
| `/api/videos/{id}` | GET | Stream video (range requests supported) |
| `/api/videos/{id}` | DELETE | Delete video + frames |
| `/api/schedule` | GET / POST | List / create scheduled jobs |
| `/api/schedule/{id}` | GET / PUT / DELETE | Get / update / delete job |
| `/api/schedule/{id}/enable` | POST | Enable job |
| `/api/schedule/{id}/disable` | POST | Disable job |
| `/api/schedule/{id}/run_now` | POST | Run job immediately |
| `/api/settings` | GET | Return all persistent settings |
| `/api/settings` | PATCH | Update one or more settings (applies stream resolution immediately) |
| `/api/settings/data` | DELETE | Delete all captures, videos, and DB records |
| `/ws/status` | WS | Real-time capture progress |

## Notes

- **Python**: must use `/usr/bin/python3` (system 3.11 with picamera2). Linuxbrew Python does not have picamera2.
- **Camera access**: only one process can hold the camera at a time. The server automatically stops the MJPEG stream before timelapse capture and restarts it when done.
- **Stream encoding**: the VideoCore hardware MJPEG encoder (`/dev/video11`) has a resolution ceiling. LensLoop automatically falls back to a software encoder (LibavMjpegEncoder via PyAV) for modes that exceed the hardware limit, so all sensor modes are available at full quality.
- **Settings persistence**: settings are saved to `data/settings.json` and loaded on startup. The default stream resolution is applied immediately when changed in the Settings page.
- **Timestamps**: all scheduler and video timestamps are displayed in SAST (UTC+2, no DST).
- **Video filenames**: `timelapse_YYYYMMDD_HHMMSS.mp4` using SAST time; DB IDs remain UUIDs.
- **Tests**: `uv run pytest backend/tests/ -v`
