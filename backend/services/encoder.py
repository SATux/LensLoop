from __future__ import annotations
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EncoderError(Exception):
    pass


@dataclass
class VideoMetadata:
    duration: float
    width: int
    height: int


class EncoderService:
    def build_video(self, frame_dir: Path, output_path: Path, fps: int) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-pattern_type", "glob",
            "-i", str(frame_dir / "frame_*.jpg"),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")[-500:]
            raise EncoderError(f"ffmpeg failed (code {result.returncode}): {stderr}")

    def build_preview(
        self, frame_dir: Path, output_path: Path, fps: int, max_frames: Optional[int] = None
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frames = sorted(frame_dir.glob("frame_*.jpg"))
        if not frames:
            raise EncoderError("No frames found for preview")

        if max_frames is not None:
            frames = frames[:max_frames]

        # Write a temp file list for ffmpeg concat demuxer
        list_path = output_path.parent / f"{output_path.stem}_list.txt"
        with open(list_path, "w") as f:
            for frame in frames:
                f.write(f"file '{frame}'\n")
                f.write(f"duration {1/fps}\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")[-500:]
                raise EncoderError(f"ffmpeg preview failed (code {result.returncode}): {stderr}")
        finally:
            try:
                list_path.unlink(missing_ok=True)
            except Exception:
                pass

    def get_video_metadata(self, path: Path) -> VideoMetadata:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            logger.warning("ffprobe failed for %s", path)
            return VideoMetadata(duration=0.0, width=0, height=0)

        try:
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            video = next((s for s in streams if s.get("codec_type") == "video"), {})
            duration = float(video.get("duration", 0.0))
            width = int(video.get("width", 0))
            height = int(video.get("height", 0))
            return VideoMetadata(duration=duration, width=width, height=height)
        except Exception as exc:
            logger.warning("ffprobe parse error: %s", exc)
            return VideoMetadata(duration=0.0, width=0, height=0)

    def extract_thumbnail(self, video_path: Path, output_path: Path, time_offset: float = 0.0) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(time_offset),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")[-300:]
            raise EncoderError(f"Thumbnail extraction failed: {stderr}")
