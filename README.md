# PiCamera Suite

Lightweight web server for a Raspberry Pi camera. Streams live MJPEG video and serves a timelapse video — no external Python packages required beyond the standard library and `picamera2`.

## Files

| File | Purpose |
|------|---------|
| `serve_video.py` | Web server (live stream + timelapse playback) |
| `capture_timelapse.py` | Capture frames from the Pi camera |
| `create_video.py` | Assemble frames into an MP4 with ffmpeg |
| `placeholder.jpg` | Fallback image when camera is unavailable |

## Quick Start

```bash
# Start the server (use system Python — picamera2 is not in Linuxbrew Python)
/usr/bin/python3 serve_video.py

# Optional: debug logging
DEBUG=1 /usr/bin/python3 serve_video.py

# Optional: custom port / resolution
PORT=8080 CAM_WIDTH=1280 CAM_HEIGHT=720 /usr/bin/python3 serve_video.py
```

Open `http://<pi-ip>:8000` in a browser.

## Timelapse Workflow

```bash
# 1. Capture frames (1 frame every 10 seconds, stop with Ctrl+C)
python3 capture_timelapse.py --output timelapse_frames --interval 10

# 2. Build video from frames
python3 create_video.py --frames timelapse_frames --output timelapse.mp4 --fps 10

# 3. The server serves timelapse.mp4 at /video automatically
```

## Routes

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/livestream_page` | Live camera stream page |
| `/livestream` | Raw MJPEG stream |
| `/video_page` | Timelapse video page |
| `/video` | Raw MP4 file |

## Dependencies

- Python 3.9+
- `python3-picamera2` — `sudo apt install python3-picamera2`
- `ffmpeg` — `sudo apt install ffmpeg` (for `create_video.py` only)
