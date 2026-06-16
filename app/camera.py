import io
import logging
import os
import threading

logger = logging.getLogger(__name__)

WIDTH = int(os.getenv('CAM_WIDTH', '640'))
HEIGHT = int(os.getenv('CAM_HEIGHT', '480'))


class FrameBuffer(io.BufferedIOBase):
    """Thread-safe buffer picamera2 writes MJPEG frames into."""
    def __init__(self):
        self.frame = None
        self.ready = threading.Condition()

    def write(self, data):
        with self.ready:
            self.frame = data
            self.ready.notify_all()
        return len(data)


buffer = FrameBuffer()
available = False


def start():
    global available
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import MJPEGEncoder
        from picamera2.outputs import FileOutput
        cam = Picamera2()
        cam.configure(cam.create_video_configuration(main={'size': (WIDTH, HEIGHT)}))
        cam.start_recording(MJPEGEncoder(), FileOutput(buffer))
        available = True
        logger.info('Camera streaming at %dx%d', WIDTH, HEIGHT)
    except Exception as exc:
        logger.warning('Camera unavailable, using placeholder: %s', exc)
