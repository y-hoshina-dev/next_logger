from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .storage_paths import get_app_data_dir


class ProfileStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (get_app_data_dir() / "profiles.json")

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

    def list_names(self) -> list[str]:
        return sorted(self._load().keys())

    def load_profile(self, name: str) -> dict[str, Any] | None:
        return self._load().get(name)

    def save_profile(self, name: str, payload: dict[str, Any]) -> None:
        data = self._load()
        data[name] = payload
        self._save(data)

    def delete_profile(self, name: str) -> None:
        data = self._load()
        if name in data:
            del data[name]
            self._save(data)
