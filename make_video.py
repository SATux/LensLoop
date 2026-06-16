#!/usr/bin/env python3
"""Assemble timelapse frames into an MP4 video using ffmpeg.

Usage:
  python3 make_video.py [--frames timelapse_frames] [--output timelapse.mp4] [--fps 10]
"""
import argparse
import subprocess
from pathlib import Path


def make_video(frames_dir: str, output: str, fps: int = 10):
    frames = Path(frames_dir)
    if not any(frames.glob('*.jpg')):
        raise FileNotFoundError(f'No .jpg files found in {frames_dir}')
    subprocess.run([
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-pattern_type', 'glob',
        '-i', str(frames / '*.jpg'),
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '28',
        '-pix_fmt', 'yuv420p',
        output,
    ], check=True)
    print(f'Video written to {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build timelapse video from frames')
    parser.add_argument('--frames', default='timelapse_frames', help='Input frames directory')
    parser.add_argument('--output', default='timelapse.mp4', help='Output video file')
    parser.add_argument('--fps', type=int, default=10, help='Playback framerate (default: 10)')
    args = parser.parse_args()
    make_video(args.frames, args.output, args.fps)
