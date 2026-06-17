from __future__ import annotations
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULTS: dict = {
    "stream_width": 640,
    "stream_height": 480,
    "capture_interval": 5,
    "capture_duration": 10,
    "capture_fps": 24,
    "capture_width": 1640,
    "capture_height": 1232,
}


class SettingsStore:
    def __init__(self, path: Path):
        self._path = path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text())
                logger.info("Settings loaded from %s", self._path)
        except Exception as exc:
            logger.warning("Could not load settings (%s), using defaults", exc)
            self._data = {}

    def all(self) -> dict:
        return {k: self._data.get(k, v) for k, v in DEFAULTS.items()}

    def get(self, key: str):
        return self._data.get(key, DEFAULTS.get(key))

    def update(self, updates: dict) -> dict:
        # Only persist known keys
        for k, v in updates.items():
            if k in DEFAULTS and v is not None:
                self._data[k] = v
        self._save()
        return self.all()

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=2))
        except Exception as exc:
            logger.error("Could not save settings: %s", exc)
