from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .storage_paths import get_app_data_dir


class AppSettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (get_app_data_dir() / "app_settings.json")

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_bool(self, key: str, default: bool = False) -> bool:
        data = self._load()
        value = data.get(key, default)
        return bool(value)

    def set_bool(self, key: str, value: bool) -> None:
        data = self._load()
        data[key] = bool(value)
        self._save(data)
