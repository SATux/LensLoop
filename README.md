# PiCamera Suite

Lightweight web server for a Raspberry Pi camera. Streams live MJPEG video and captures timelapse sequences with automatic MP4 assembly.

## Requirements

```bash
sudo apt install python3-picamera2 ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
# Add uv to PATH (add to ~/.zshrc or ~/.bashrc to make permanent)
export PATH="$HOME/.local/bin:$PATH"

# Create venv using system Python (required — apt-installed picamera2 is not on PyPI)
uv venv --python /usr/bin/python3 --system-site-packages
uv sync
```

## Usage

### Web server

```bash
uv run serve

# Optional: debug logging or custom port/resolution
DEBUG=1 uv run serve
PORT=8080 CAM_WIDTH=1280 CAM_HEIGHT=720 uv run serve
```

Open `http://<pi-ip>:8000` in a browser.

### Timelapse via web UI

Navigate to **Setup Timelapse** from the landing page. Set the capture interval, total duration, and output framerate, then click **Start Capture**. The page polls for progress and shows a link to the finished video when done.

> The live stream pauses while timelapse capture runs and resumes automatically when it finishes.

### Timelapse via CLI

```bash
# Capture frames (Ctrl+C to stop early)
uv run capture --output timelapse_frames --interval 10 --count 120

# Assemble frames into video
uv run make-video --frames timelapse_frames --output timelapse.mp4 --fps 10
```

## Project Structure

```
pi-camera-suite/
├── app/
│   ├── __init__.py
│   ├── camera.py      # Picamera2 MJPEG stream, FrameBuffer, start/stop
│   ├── capture.py     # CLI timelapse frame capture (entry point: capture)
│   ├── server.py      # HTTP handler, routing, ThreadingMixIn TCPServer
│   ├── timelapse.py   # Web timelapse state machine (idle|capturing|building|done|error)
│   └── video.py       # ffmpeg video assembly (entry point: make-video)
├── static/
│   ├── index.html            # Landing page
│   ├── timelapse_page.html   # Timelapse setup and status UI
│   ├── video_page.html       # Timelapse video player
│   ├── livestream_page.html  # Live camera stream page
│   └── placeholder.jpg       # Shown when camera is unavailable
├── serve.py          # Direct-run fallback: /usr/bin/python3 serve.py
└── pyproject.toml
```

## Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page |
| `/livestream_page` | GET | Live camera stream page |
| `/livestream` | GET | Raw MJPEG stream |
| `/video_page` | GET | Timelapse video player page |
| `/video` | GET | Most recently created `timelapse*.mp4` |
| `/timelapse_page` | GET | Timelapse setup and status page |
| `/timelapse/start` | POST | Start timelapse (`{interval, duration, fps}`) |
| `/timelapse/stop` | POST | Abort running timelapse |
| `/timelapse/status` | GET | Current state as JSON |

## Notes

- **Python**: must use `/usr/bin/python3` (system 3.11). Linuxbrew Python does not have picamera2.
- **Video files**: `timelapse*.mp4` files are written to the project root and excluded from git. Frames in `timelapse_frames/` are deleted automatically after successful video assembly.
- **Camera access**: only one process can hold the camera at a time. The web timelapse runner stops the MJPEG stream before capture and restarts it when done. Do not run `uv run capture` while the server is streaming.
