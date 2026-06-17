from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, field_validator


@dataclass
class CaptureMode:
    width: int
    height: int
    megapixels: float
    max_fps: float
    bit_depth: int
    full_fov: bool
    label: str
    description: str

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "megapixels": self.megapixels,
            "max_fps": self.max_fps,
            "bit_depth": self.bit_depth,
            "full_fov": self.full_fov,
            "label": self.label,
            "description": self.description,
        }


class CameraCapabilities(BaseModel):
    model: str
    available: bool
    modes: list[dict]


class TimelapsStartRequest(BaseModel):
    interval: int
    duration: int
    fps: int
    capture_width: int
    capture_height: int

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if not (1 <= v <= 3600):
            raise ValueError("interval must be between 1 and 3600 seconds")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if not (1 <= v <= 1440):
            raise ValueError("duration must be between 1 and 1440 minutes")
        return v

    @field_validator("fps")
    @classmethod
    def validate_fps(cls, v: int) -> int:
        if v not in (5, 10, 15, 24, 30):
            raise ValueError("fps must be one of 5, 10, 15, 24, 30")
        return v


class TimelapsStatusResponse(BaseModel):
    run_id: Optional[str]
    status: str
    captured: int
    total: int
    message: str
    video_id: Optional[str]
    started_at: Optional[str]
    capture_width: Optional[int]
    capture_height: Optional[int]


class PreviewStatusResponse(BaseModel):
    generating: bool
    ready: bool
    url: Optional[str]


class VideoResponse(BaseModel):
    id: str
    filename: str
    created_at: str
    size_bytes: int
    duration_seconds: float
    frame_count: int
    fps: int
    width: int
    height: int
    run_id: Optional[str]


class ScheduleCreateRequest(BaseModel):
    name: str
    cron_expression: str
    interval: int
    duration: int
    fps: int
    capture_width: int
    capture_height: int

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if not (1 <= v <= 3600):
            raise ValueError("interval must be between 1 and 3600 seconds")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if not (1 <= v <= 1440):
            raise ValueError("duration must be between 1 and 1440 minutes")
        return v

    @field_validator("fps")
    @classmethod
    def validate_fps(cls, v: int) -> int:
        if v not in (5, 10, 15, 24, 30):
            raise ValueError("fps must be one of 5, 10, 15, 24, 30")
        return v


class ScheduleResponse(BaseModel):
    id: str
    name: str
    cron_expression: str
    interval: int
    duration: int
    fps: int
    capture_width: int
    capture_height: int
    enabled: bool
    next_run_at: Optional[str]
    last_run_at: Optional[str]


class WsStatusMessage(BaseModel):
    event: str
    data: dict
