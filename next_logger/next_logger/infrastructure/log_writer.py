from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
import threading
from typing import TextIO

from next_logger.application.preflight import build_preview_path
from next_logger.domain.models import ConnectionConfig, SessionConfig, SessionStats


class SessionLogWriter:
    def __init__(self, config: SessionConfig) -> None:
        self._lock = threading.Lock()
        self._config = config
        self._started_at = datetime.now()
        self.session_dir = build_preview_path(config, now=self._started_at)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.segment_index = 1
        self._raw_file: TextIO | None = None
        self._data_file: TextIO | None = None
        self._error_file: TextIO | None = None
        self._csv_writer: csv.writer | None = None
        self._segment_files: list[dict[str, str]] = []
        self._closed = False

        self._open_segment_files()

    @property
    def log_format(self) -> str:
        return self._config.log_format

    def _segment_tag(self) -> str:
        return f"part{self.segment_index:02d}"

    def _open_segment_files(self) -> None:
        tag = self._segment_tag()
        raw_path = self.session_dir / f"raw_{tag}.log"
        error_path = self.session_dir / f"error_{tag}.log"

        if self._config.log_format == "csv":
            data_path = self.session_dir / f"data_{tag}.csv"
        elif self._config.log_format == "jsonl":
            data_path = self.session_dir / f"data_{tag}.jsonl"
        else:
            data_path = self.session_dir / f"data_{tag}.txt"

        self._raw_file = raw_path.open("a", encoding="utf-8", newline="")
        self._error_file = error_path.open("a", encoding="utf-8", newline="")
        self._data_file = data_path.open("a", encoding="utf-8", newline="")

        self._csv_writer = None
        if self._config.log_format == "csv":
            self._csv_writer = csv.writer(self._data_file)
            if data_path.stat().st_size == 0:
                self._csv_writer.writerow(["timestamp", "log", "is_error"])
                self._data_file.flush()

        self._segment_files.append(
            {
                "segment": tag,
                "raw": str(raw_path),
                "data": str(data_path),
                "error": str(error_path),
            }
        )

    def _close_segment_files(self) -> None:
        if self._raw_file:
            self._raw_file.close()
            self._raw_file = None
        if self._data_file:
            self._data_file.close()
            self._data_file = None
        if self._error_file:
            self._error_file.close()
            self._error_file = None
        self._csv_writer = None

    def rotate_segment(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._close_segment_files()
            self.segment_index += 1
            self._open_segment_files()

    def write_line(self, timestamp: datetime, line: str, is_error: bool) -> bool:
        with self._lock:
            if self._closed:
                return False
            try:
                ts = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                assert self._raw_file is not None
                assert self._data_file is not None
                assert self._error_file is not None

                self._raw_file.write(f"{ts}\t{line}\n")

                if self._config.log_format == "csv":
                    assert self._csv_writer is not None
                    self._csv_writer.writerow([ts, line, is_error])
                elif self._config.log_format == "jsonl":
                    payload = {"timestamp": ts, "log": line, "is_error": is_error}
                    self._data_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
                else:
                    self._data_file.write(line + "\n")

                if is_error:
                    self._error_file.write(f"{ts}\t{line}\n")

                self._raw_file.flush()
                self._data_file.flush()
                self._error_file.flush()
                return True
            except OSError:
                return False

    def close(
        self,
        status: str,
        stats: SessionStats,
        reason: str = "",
        connection: ConnectionConfig | None = None,
    ) -> Path:
        with self._lock:
            if self._closed:
                return self.session_dir / "manifest.json"

            self._close_segment_files()
            finished_at = datetime.now()
            manifest = {
                "session": {
                    "started_at": self._started_at.isoformat(timespec="seconds"),
                    "ended_at": finished_at.isoformat(timespec="seconds"),
                    "status": status,
                    "reason": reason,
                    "session_dir": str(self.session_dir),
                    "segment_count": self.segment_index,
                },
                "settings": {
                    "product": self._config.product,
                    "serial_number": self._config.serial_number,
                    "comment": self._config.comment,
                    "date": self._config.date,
                    "save_dir": str(self._config.save_dir),
                    "log_format": self._config.log_format,
                    "error_keywords": list(self._config.error_keywords),
                    "resume_policy": self._config.resume_policy,
                    "retention_max_sessions": self._config.retention_max_sessions,
                    "retention_max_age_days": self._config.retention_max_age_days,
                },
                "connection": (
                    {
                        "port": connection.port,
                        "baudrate": connection.baudrate,
                        "parity": connection.parity,
                        "bytesize": connection.bytesize,
                        "stopbits": connection.stopbits,
                        "timeout": connection.timeout,
                        "auto_reconnect": connection.auto_reconnect,
                        "reconnect_max_retries": connection.reconnect_max_retries,
                        "reconnect_backoff_mode": connection.reconnect_backoff_mode,
                        "reconnect_interval_sec": connection.reconnect_interval_sec,
                        "reconnect_max_interval_sec": connection.reconnect_max_interval_sec,
                    }
                    if connection is not None
                    else {}
                ),
                "stats": {
                    "received_lines": stats.received_lines,
                    "dropped_lines": stats.dropped_lines,
                    "write_failures": stats.write_failures,
                    "error_lines": stats.error_lines,
                    "last_error": stats.last_error,
                    "reconnect_attempts": stats.reconnect_attempts,
                    "reconnect_events": stats.reconnect_events,
                },
                "segments": self._segment_files,
            }

            manifest_path = self.session_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self._closed = True
            return manifest_path
