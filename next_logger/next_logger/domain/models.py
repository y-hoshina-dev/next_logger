from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


LogFormat = Literal["txt", "csv", "jsonl"]
ResumePolicy = Literal["append", "new_segment"]
ReconnectBackoffMode = Literal["fixed", "exponential"]


@dataclass(frozen=True)
class ConnectionConfig:
    port: str
    baudrate: int = 9600
    parity: str = "N"
    bytesize: int = 8
    stopbits: float = 1.0
    timeout: float = 1.0
    auto_reconnect: bool = True
    reconnect_max_retries: int = 5
    reconnect_interval_sec: float = 2.0
    reconnect_backoff_mode: ReconnectBackoffMode = "fixed"
    reconnect_max_interval_sec: float = 10.0


@dataclass(frozen=True)
class SessionConfig:
    product: str = ""
    serial_number: str = ""
    comment: str = ""
    date: str = ""
    save_dir: Path = Path(".")
    log_format: LogFormat = "txt"
    error_keywords: tuple[str, ...] = ("ERROR", "ERR", "FATAL", "CRITICAL", "EXCEPTION", "FAIL", "NG")
    resume_policy: ResumePolicy = "append"
    retention_max_sessions: int = 0
    retention_max_age_days: int = 0


@dataclass
class SessionStats:
    received_lines: int = 0
    dropped_lines: int = 0
    write_failures: int = 0
    error_lines: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None
    last_error: str = ""
    session_dir: Path | None = None
    segment_count: int = 1
    reconnect_attempts: int = 0
    reconnect_events: list[dict[str, str]] = field(default_factory=list)
