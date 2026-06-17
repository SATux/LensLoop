import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
CAM_WIDTH = int(os.getenv("CAM_WIDTH", "640"))
CAM_HEIGHT = int(os.getenv("CAM_HEIGHT", "480"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
PREVIEW_TTL_SECONDS = int(os.getenv("PREVIEW_TTL_SECONDS", "60"))
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

FRAMES_DIR = DATA_DIR / "frames"
PREVIEWS_DIR = DATA_DIR / "previews"
VIDEOS_DIR = DATA_DIR / "videos"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
DB_PATH = DATA_DIR / "timelapse.db"
