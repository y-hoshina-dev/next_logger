from __future__ import annotations

from pathlib import Path


APP_DIR_NAME = ".next_logger"


def get_app_data_dir() -> Path:
    root = Path.home() / APP_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root
