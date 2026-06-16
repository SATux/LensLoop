#!/usr/bin/env python3
import http.server
import socketserver
import io
import logging
import os
import sys
import threading
import time
from pathlib import Path

PORT = int(os.getenv('PORT', '8000'))
CAM_WIDTH = int(os.getenv('CAM_WIDTH', '640'))
CAM_HEIGHT = int(os.getenv('CAM_HEIGHT', '480'))
DEBUG = os.getenv('DEBUG') == '1' or '--debug' in sys.argv

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='[%(levelname)s] %(asctime)s %(message)s',
)
logger = logging.getLogger(__name__)


class _FrameBuffer(io.BufferedIOBase):
    """Shared buffer picamera2 writes MJPEG frames into."""
    def __init__(self):
        self.frame = None
        self.ready = threading.Condition()

    def write(self, data):
        with self.ready:
            self.frame = data
            self.ready.notify_all()
        return len(data)


_buf = _FrameBuffer()
_camera_ok = False


def _start_camera():
    global _camera_ok
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import MJPEGEncoder
        from picamera2.outputs import FileOutput
        cam = Picamera2()
        cam.configure(cam.create_video_configuration(main={'size': (CAM_WIDTH, CAM_HEIGHT)}))
        cam.start_recording(MJPEGEncoder(), FileOutput(_buf))
        _camera_ok = True
        logger.info(f"Camera streaming at {CAM_WIDTH}x{CAM_HEIGHT}")
    except Exception as exc:
        logger.warning(f"Camera unavailable, using placeholder: {exc}")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    # ---- routing ----

    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/livestream':
            self._stream()
        else:
            self._static(p)

    def do_HEAD(self):
        self._static(self.path.split('?')[0])

    def _static(self, path):
        routes = {
            '/video':            (Path('timelapse.mp4'),       'video/mp4'),
            '/':                 (Path('index.html'),          'text/html; charset=utf-8'),
            '/index.html':       (Path('index.html'),          'text/html; charset=utf-8'),
            '/video_page':       (Path('video_page.html'),     'text/html; charset=utf-8'),
            '/livestream_page':  (Path('livestream_page.html'),'text/html; charset=utf-8'),
        }
        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if path not in routes:
            self.send_error(404)
            return
        self._send_file(*routes[path])

    # ---- handlers ----

    def _send_file(self, fpath, ctype):
        if not fpath.is_file():
            self.send_error(404, f'{fpath.name} not found')
            return
        size = fpath.stat().st_size
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(size))
        self.end_headers()
        if self.command == 'GET':
            with open(fpath, 'rb') as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)

    def _stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        try:
            if _camera_ok:
                while True:
                    with _buf.ready:
                        _buf.ready.wait()
                        frame = _buf.frame
                    self._write_frame(frame)
            else:
                placeholder = Path('placeholder.jpg')
                if not placeholder.is_file():
                    return
                frame = placeholder.read_bytes()
                while True:
                    self._write_frame(frame)
                    time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            logger.debug('Stream closed: %s', exc)

    def _write_frame(self, data):
        self.wfile.write(
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + str(len(data)).encode() + b'\r\n'
            b'\r\n' + data + b'\r\n'
        )
        self.wfile.flush()


class _Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    _start_camera()
    logger.info('Listening on :%d', PORT)
    with _Server(('', PORT), Handler) as httpd:
        httpd.serve_forever()
