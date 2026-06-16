# PiCamera Suite

Lightweight web server for a Raspberry Pi camera. Streams live MJPEG video and serves a timelapse video.

## Requirements

```bash
sudo apt install python3-picamera2 ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
# Create venv using system Python (which has apt-installed picamera2)
uv venv --python /usr/bin/python3 --system-site-packages
uv sync
```

## Usage

```bash
# Start the web server
uv run serve

# Optional: debug logging or custom port/resolution
DEBUG=1 uv run serve
PORT=8080 CAM_WIDTH=1280 CAM_HEIGHT=720 uv run serve

# Capture timelapse frames (Ctrl+C to stop)
uv run capture --output timelapse_frames --interval 10

# Assemble frames into video
uv run make-video --frames timelapse_frames --output timelapse.mp4 --fps 10
```

Open `http://<pi-ip>:8000` in a browser.

## Project Structure

```
pi-camera-suite/
├── app/
│   ├── camera.py     # camera init and MJPEG frame buffer
│   ├── capture.py    # timelapse frame capture (entry point: capture)
│   ├── server.py     # HTTP handler, routing, server setup
│   └── video.py      # ffmpeg video assembly (entry point: make-video)
├── static/           # web assets
│   ├── index.html
│   ├── video_page.html
│   ├── livestream_page.html
│   └── placeholder.jpg
├── serve.py          # direct-run fallback (/usr/bin/python3 serve.py)
└── pyproject.toml
```

## Routes

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/livestream_page` | Live camera stream page |
| `/livestream` | Raw MJPEG stream |
| `/video_page` | Timelapse video page |
| `/video` | Raw MP4 file |
