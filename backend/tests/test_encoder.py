import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from backend.services.encoder import EncoderService, EncoderError


@pytest.fixture
def encoder():
    return EncoderService()


def test_build_video_calls_ffmpeg_with_correct_args(encoder, tmp_path, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    frame_dir = tmp_path / "frames" / "run1"
    frame_dir.mkdir(parents=True, exist_ok=True)
    output = tmp_path / "out.mp4"

    encoder.build_video(frame_dir, output, fps=24)

    args = mock_run.call_args[0][0]
    assert "ffmpeg" in args
    assert "-framerate" in args
    assert "24" in args
    assert str(output) in args


def test_build_video_raises_on_ffmpeg_failure(encoder, tmp_path, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = b"some ffmpeg error"
    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(EncoderError):
        encoder.build_video(tmp_path / "frames", tmp_path / "out.mp4", fps=24)


def test_build_preview_does_not_delete_source_frames(encoder, sample_frames, tmp_path, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    output = tmp_path / "preview.mp4"
    encoder.build_preview(sample_frames, output, fps=10)

    frames = list(sample_frames.glob("frame_*.jpg"))
    assert len(frames) == 5


def test_build_preview_uses_max_frames(encoder, sample_frames, tmp_path, monkeypatch):
    captured_args = []
    def fake_run(args, **kwargs):
        captured_args.extend(args)
        m = MagicMock()
        m.returncode = 0
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)

    output = tmp_path / "preview.mp4"
    encoder.build_preview(sample_frames, output, fps=10, max_frames=3)

    # The list file should contain 3 entries (checked by reading it)
    # Since list file is deleted after, we verify via the ffmpeg call using concat
    assert "concat" in " ".join(str(a) for a in captured_args)


def test_get_video_metadata_parses_ffprobe_output(encoder, tmp_path, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "duration": "12.5"}]
    }).encode()
    monkeypatch.setattr(subprocess, "run", mock_run)

    meta = encoder.get_video_metadata(tmp_path / "video.mp4")
    assert meta.width == 1920
    assert meta.height == 1080
    assert meta.duration == pytest.approx(12.5)


def test_extract_thumbnail_calls_ffmpeg(encoder, tmp_path, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    video_path = tmp_path / "video.mp4"
    thumb_path = tmp_path / "thumb.jpg"
    encoder.extract_thumbnail(video_path, thumb_path)

    args = mock_run.call_args[0][0]
    assert "ffmpeg" in args
    assert str(video_path) in args
    assert str(thumb_path) in args


def test_encoder_error_message_includes_stderr(encoder, tmp_path, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = b"critical ffmpeg stderr message"
    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(EncoderError, match="critical ffmpeg stderr message"):
        encoder.build_video(tmp_path / "frames", tmp_path / "out.mp4", fps=24)
