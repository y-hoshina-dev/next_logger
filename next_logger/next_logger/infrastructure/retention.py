from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import shutil


def _is_session_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    return (path / "manifest.json").exists()


def _remove_dir(path: Path) -> bool:
    try:
        shutil.rmtree(path)
        return True
    except OSError:
        return False


def apply_retention_policy(
    base_dir: Path,
    max_sessions: int,
    max_age_days: int,
    keep_dirs: set[Path] | None = None,
) -> dict[str, int]:
    keep_dirs = keep_dirs or set()
    removed_age = 0
    removed_count = 0

    try:
        candidates = [p for p in base_dir.iterdir() if _is_session_dir(p) and p not in keep_dirs]
    except OSError:
        return {"removed_age": 0, "removed_count": 0}

    now = datetime.now()
    if max_age_days > 0:
        threshold = now - timedelta(days=max_age_days)
        next_candidates: list[Path] = []
        for path in candidates:
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified < threshold:
                if _remove_dir(path):
                    removed_age += 1
            else:
                next_candidates.append(path)
        candidates = next_candidates

    if max_sessions > 0 and len(candidates) > max_sessions:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        to_remove = candidates[max_sessions:]
        for path in to_remove:
            if _remove_dir(path):
                removed_count += 1

    return {"removed_age": removed_age, "removed_count": removed_count}
