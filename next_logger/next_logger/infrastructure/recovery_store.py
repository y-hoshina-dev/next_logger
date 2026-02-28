from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .storage_paths import get_app_data_dir


class RecoveryStore:
    def __init__(self, marker_path: Path | None = None) -> None:
        self.marker_path = marker_path or (get_app_data_dir() / "active_session.json")

    def write_marker(self, payload: dict[str, Any]) -> None:
        self.marker_path.parent.mkdir(parents=True, exist_ok=True)
        self.marker_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_marker(self) -> dict[str, Any] | None:
        if not self.marker_path.exists():
            return None
        try:
            return json.loads(self.marker_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def clear_marker(self) -> None:
        if self.marker_path.exists():
            self.marker_path.unlink()
