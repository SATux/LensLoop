# PiCamera Suite

Lightweight web server for a Raspberry Pi camera. Streams live MJPEG video and serves a timelapse video — no pip packages required, only `picamera2` and `ffmpeg` from apt.

## Project Structure

```
pi-camera-suite/
├── app/
│   ├── camera.py         # camera init and MJPEG frame buffer
│   └── server.py         # HTTP handler, routing, server setup
├── static/               # web assets served by the server
│   ├── index.html
│   ├── video_page.html
│   ├── livestream_page.html
│   └── placeholder.jpg
├── capture.py            # CLI: capture timelapse frames
├── make_video.py         # CLI: assemble frames into MP4
├── serve.py              # entry point
└── requirements.txt
```

## Quick Start

```bash
# Use system Python — picamera2 is not available in Linuxbrew Python
/usr/bin/python3 serve.py

# Optional: debug logging
DEBUG=1 /usr/bin/python3 serve.py

# Optional: custom port / resolution
PORT=8080 CAM_WIDTH=1280 CAM_HEIGHT=720 /usr/bin/python3 serve.py
```

Open `http://<pi-ip>:8000` in a browser.

## Timelapse Workflow

```bash
# 1. Capture frames (1 frame every 10 seconds, Ctrl+C to stop)
/usr/bin/python3 capture.py --output timelapse_frames --interval 10

# 2. Assemble into video
python3 make_video.py --frames timelapse_frames --output timelapse.mp4 --fps 10

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

```bash
sudo apt install python3-picamera2 ffmpeg
```
