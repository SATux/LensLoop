import http.server
import json
import logging
import os
import socketserver
import sys
import time
from pathlib import Path

from . import camera, timelapse

PORT = int(os.getenv('PORT', '8000'))
DEBUG = os.getenv('DEBUG') == '1' or '--debug' in sys.argv

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='[%(levelname)s] %(asctime)s %(message)s',
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
STATIC = ROOT / 'static'


def _latest_video() -> Path | None:
    videos = sorted(ROOT.glob('timelapse*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)
    return videos[0] if videos else None


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    # ---- routing ----

    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/livestream':
            self._stream()
        elif p == '/timelapse/status':
            self._json(timelapse.status())
        elif p == '/video':
            v = _latest_video()
            if v:
                self._send_file(v, 'video/mp4')
            else:
                self.send_error(404, 'No timelapse video found')
        else:
            self._static(p)

    def do_HEAD(self):
        p = self.path.split('?')[0]
        if p == '/video':
            v = _latest_video()
            if v:
                self._send_file(v, 'video/mp4')
            else:
                self.send_error(404)
        else:
            self._static(p)

    def do_POST(self):
        p = self.path.split('?')[0]
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if p == '/timelapse/start':
            interval = float(body.get('interval', 5))
            duration = float(body.get('duration', 10))
            fps      = int(body.get('fps', 10))
            if interval <= 0 or duration <= 0:
                self._json({'ok': False, 'error': 'interval and duration must be > 0'}, 400)
                return
            ok, err = timelapse.start(interval, duration, fps)
            self._json({'ok': ok, 'error': err})

        elif p == '/timelapse/stop':
            timelapse.stop()
            self._json({'ok': True})

        else:
            self.send_error(404)

    # ---- helpers ----

    def _static(self, path):
        routes = {
            '/':                  (STATIC / 'index.html',           'text/html; charset=utf-8'),
            '/index.html':        (STATIC / 'index.html',           'text/html; charset=utf-8'),
            '/video_page':        (STATIC / 'video_page.html',      'text/html; charset=utf-8'),
            '/livestream_page':   (STATIC / 'livestream_page.html', 'text/html; charset=utf-8'),
            '/timelapse_page':    (STATIC / 'timelapse_page.html',  'text/html; charset=utf-8'),
        }
        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if path not in routes:
            self.send_error(404)
            return
        self._send_file(*routes[path])

    def _send_file(self, fpath, ctype):
        if not fpath.is_file():
            self.send_error(404, f'{fpath.name} not found')
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(fpath.stat().st_size))
        self.end_headers()
        if self.command == 'GET':
            with open(fpath, 'rb') as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        try:
            if camera.available:
                while True:
                    with camera.buffer.ready:
                        camera.buffer.ready.wait()
                        frame = camera.buffer.frame
                    self._write_frame(frame)
            else:
                frame = (STATIC / 'placeholder.jpg').read_bytes()
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


def run():
    camera.start()
    logger.info('Listening on :%d', PORT)
    with _Server(('', PORT), Handler) as httpd:
        httpd.serve_forever()
