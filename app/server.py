import http.server
import logging
import os
import socketserver
import sys
import time
from pathlib import Path

from . import camera

PORT = int(os.getenv('PORT', '8000'))
DEBUG = os.getenv('DEBUG') == '1' or '--debug' in sys.argv

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='[%(levelname)s] %(asctime)s %(message)s',
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
STATIC = ROOT / 'static'


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

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
            '/':                (STATIC / 'index.html',           'text/html; charset=utf-8'),
            '/index.html':      (STATIC / 'index.html',           'text/html; charset=utf-8'),
            '/video_page':      (STATIC / 'video_page.html',      'text/html; charset=utf-8'),
            '/livestream_page': (STATIC / 'livestream_page.html', 'text/html; charset=utf-8'),
            '/video':           (ROOT / 'timelapse.mp4',          'video/mp4'),
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
