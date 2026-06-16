#!/usr/bin/env python3
"""Capture timelapse frames from Raspberry Pi camera.

Usage:
  /usr/bin/python3 capture.py --output timelapse_frames [--interval 5] [--count 100]
"""
import argparse
import os
import time
from datetime import datetime
from picamera2 import Picamera2


def main():
    parser = argparse.ArgumentParser(description='Raspberry Pi timelapse capture')
    parser.add_argument('--output', required=True, help='Directory to store frames')
    parser.add_argument('--interval', type=float, default=5.0, help='Seconds between frames (default: 5)')
    parser.add_argument('--count', type=int, default=None, help='Frame limit (default: unlimited)')
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    cam = Picamera2()
    cam.configure(cam.create_still_configuration(main={'size': (args.width, args.height)}))
    cam.start()
    print(f"Capturing to '{args.output}' every {args.interval}s — Ctrl+C to stop.")

    captured = 0
    try:
        while args.count is None or captured < args.count:
            ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            path = os.path.join(args.output, f'frame_{ts}.jpg')
            cam.capture_file(path)
            print(f'[{captured + 1}] {path}')
            captured += 1
            if args.count is None or captured < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f'\nStopped after {captured} frames.')
    finally:
        cam.stop()


if __name__ == '__main__':
    main()
