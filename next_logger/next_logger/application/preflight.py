from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import tempfile

from next_logger.application.log_markers import DEFAULT_CUSTOM_ERROR_KEYWORDS
from next_logger.domain.models import ConnectionConfig, SessionConfig


_INVALID_FILENAME_CHARS = re.compile(r"[<>:\"/\\|?*\x00-\x1F]")
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}
_SUPPORTED_FORMATS = {"txt", "csv", "jsonl"}
_SUPPORTED_BACKOFF_MODES = {"fixed", "exponential"}


@dataclass(frozen=True)
class PreflightResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    preview_path: Path


def sanitize_component(value: str, fallback: str = "na") -> str:
    text = _INVALID_FILENAME_CHARS.sub("_", value.strip())
    text = text.rstrip(". ")
    if not text:
        text = fallback
    if text.upper() in _RESERVED_NAMES:
        text = f"_{text}"
    return text


def normalize_error_keywords(raw: tuple[str, ...] | list[str] | str) -> tuple[str, ...]:
    if isinstance(raw, str):
        items = [part.strip() for part in raw.split(",")]
    else:
        items = [part.strip() for part in raw]
    filtered = [item for item in items if item]
    if not filtered:
        return DEFAULT_CUSTOM_ERROR_KEYWORDS
    return tuple(filtered)


def build_session_stub(config: SessionConfig) -> str:
    parts = [
        sanitize_component(config.product, "product"),
        sanitize_component(config.serial_number, "serial"),
        sanitize_component(config.comment, "memo"),
        sanitize_component(config.date or datetime.now().strftime("%Y%m%d"), "date"),
    ]
    return "_".join(parts)


def build_preview_path(config: SessionConfig, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    session_id = now.strftime("%Y%m%d_%H%M%S")
    base_dir = Path(config.save_dir)
    return base_dir / f"{session_id}_{build_session_stub(config)}"


def _is_writable_directory(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="next_logger_", dir=path)
        return True
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def run_preflight(
    connection: ConnectionConfig,
    session: SessionConfig,
    available_ports: list[str],
) -> PreflightResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not connection.port:
        errors.append("COMポートを選択してください。")
    elif available_ports and connection.port not in available_ports:
        warnings.append(f"選択ポート {connection.port} は現在の一覧に見つかりません。")

    if connection.baudrate <= 0:
        errors.append("ボーレートは正の整数で指定してください。")

    if connection.timeout <= 0:
        errors.append("タイムアウトは0より大きい値にしてください。")

    if connection.reconnect_max_retries < 0:
        errors.append("再接続回数は0以上で指定してください。")

    if connection.reconnect_interval_sec <= 0:
        errors.append("再接続待機秒数は0より大きい値にしてください。")

    if connection.reconnect_backoff_mode not in _SUPPORTED_BACKOFF_MODES:
        errors.append("再接続モードは fixed / exponential のいずれかを選択してください。")

    if connection.reconnect_max_interval_sec <= 0:
        errors.append("再接続の最大待機秒数は0より大きい値にしてください。")

    if connection.reconnect_max_interval_sec < connection.reconnect_interval_sec:
        errors.append("再接続の最大待機秒数は基本待機秒数以上にしてください。")

    if session.log_format not in _SUPPORTED_FORMATS:
        errors.append("保存形式は txt / csv / jsonl のいずれかを選択してください。")

    if session.retention_max_sessions < 0:
        errors.append("保持セッション数は0以上で指定してください。")

    if session.retention_max_age_days < 0:
        errors.append("保持日数は0以上で指定してください。")

    try:
        save_dir = Path(session.save_dir)
        if not _is_writable_directory(save_dir):
            errors.append(f"保存先に書き込めません: {save_dir}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"保存先の確認に失敗しました: {exc}")

    preview_path = build_preview_path(session)
    if len(str(preview_path)) > 240:
        warnings.append("保存パスが長すぎる可能性があります。項目を短くしてください。")

    return PreflightResult(errors=tuple(errors), warnings=tuple(warnings), preview_path=preview_path)
