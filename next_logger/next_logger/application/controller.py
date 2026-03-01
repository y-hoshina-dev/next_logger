from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
import queue
import threading
from typing import Any

from serial.tools import list_ports

from next_logger.application.preflight import (
    build_preview_path,
    normalize_error_keywords,
    run_preflight,
)
from next_logger.application.log_markers import classify_log_line
from next_logger.domain import AppState, ConnectionConfig, SessionConfig, SessionStats, StateMachine
from next_logger.infrastructure import (
    ProfileStore,
    RecoveryStore,
    SerialWorker,
    SessionLogWriter,
    apply_retention_policy,
)


class LoggerController:
    def __init__(self) -> None:
        self._state_machine = StateMachine()
        self._stats = SessionStats()
        self._events: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=5000)
        self._worker: SerialWorker | None = None
        self._writer: SessionLogWriter | None = None
        self._connection: ConnectionConfig | None = None
        self._session: SessionConfig | None = None
        self._profile_store = ProfileStore()
        self._recovery_store = RecoveryStore()
        self._lock = threading.Lock()

    @property
    def state(self) -> AppState:
        return self._state_machine.state

    def list_ports(self) -> list[str]:
        return [port.device for port in list_ports.comports()]

    def build_preview_path(self, session: SessionConfig) -> Path:
        return build_preview_path(self._normalize_session(session))

    def get_stats_snapshot(self) -> SessionStats:
        with self._lock:
            return replace(self._stats)

    def start(self, connection: ConnectionConfig, session: SessionConfig) -> tuple[str, ...]:
        normalized_session = self._normalize_session(session)
        preflight = run_preflight(connection, normalized_session, self.list_ports())
        if preflight.errors:
            self._emit_event({"type": "preflight_failed", "errors": list(preflight.errors)})
            return preflight.errors

        if self.state not in {AppState.IDLE, AppState.READY, AppState.ERROR}:
            return (f"Cannot start from state: {self.state.value}",)

        with self._lock:
            self._connection = connection
            self._session = normalized_session
            self._stats = SessionStats(start_time=datetime.now())

        self._move_state(AppState.READY)

        try:
            self._writer = SessionLogWriter(normalized_session)
        except OSError as exc:
            self._move_state(AppState.ERROR)
            with self._lock:
                self._stats.last_error = str(exc)
            message = f"Failed to create log files: {exc}"
            self._emit_event({"type": "error", "message": message})
            return (message,)

        with self._lock:
            self._stats.session_dir = self._writer.session_dir

        self._write_recovery_marker()

        self._worker = SerialWorker(
            connection=connection,
            on_open=self._on_serial_open,
            on_line=self._on_serial_line,
            on_error=self._on_serial_error,
            on_reconnect=self._on_serial_reconnect,
        )
        self._worker.start()

        self._move_state(AppState.RUNNING)
        self._emit_event(
            {
                "type": "session_started",
                "session_dir": str(self._writer.session_dir),
                "warnings": list(preflight.warnings),
            }
        )
        return ()

    def pause(self) -> None:
        if self.state != AppState.RUNNING or self._worker is None:
            return
        self._worker.pause()
        self._move_state(AppState.PAUSED)
        self._emit_event({"type": "status", "message": "Paused."})

    def resume(self, session: SessionConfig | None = None) -> None:
        if self.state != AppState.PAUSED or self._worker is None:
            return

        normalized_session = self._session
        if session is not None:
            normalized_session = self._normalize_session(session)

        if normalized_session is not None and self._writer is not None:
            if normalized_session.resume_policy == "new_segment":
                self._writer.rotate_segment()
                with self._lock:
                    self._stats.segment_count = self._writer.segment_index

            with self._lock:
                self._session = normalized_session

        self._worker.resume()
        self._move_state(AppState.RUNNING)
        self._emit_event({"type": "status", "message": "Resumed."})

    def stop(self, reason: str = "user_stop") -> None:
        current_state = self.state
        if current_state in {AppState.RUNNING, AppState.PAUSED}:
            self._move_state(AppState.STOPPING)
        elif current_state == AppState.READY:
            self._move_state(AppState.IDLE)
            return
        elif current_state not in {AppState.ERROR, AppState.STOPPING}:
            return

        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.stop()
            if threading.current_thread() is not worker:
                worker.join(timeout=2.0)

        with self._lock:
            self._stats.end_time = datetime.now()

        writer = self._writer
        self._writer = None
        manifest_path = None
        retention_result = {"removed_age": 0, "removed_count": 0}
        if writer is not None:
            manifest_path = writer.close(
                status="stopped" if reason == "user_stop" else "error",
                stats=self.get_stats_snapshot(),
                reason=reason,
                connection=self._connection,
            )

        session = self._session
        if session is not None:
            keep_dirs = {self._stats.session_dir} if self._stats.session_dir else set()
            retention_result = apply_retention_policy(
                base_dir=session.save_dir,
                max_sessions=session.retention_max_sessions,
                max_age_days=session.retention_max_age_days,
                keep_dirs=keep_dirs,
            )

        self._recovery_store.clear_marker()

        if self.state in {AppState.STOPPING, AppState.ERROR, AppState.READY}:
            self._move_state(AppState.IDLE)

        self._emit_event(
            {
                "type": "session_stopped",
                "reason": reason,
                "manifest": str(manifest_path) if manifest_path else "",
                "retention": retention_result,
            }
        )

    def shutdown(self) -> None:
        if self.state in {AppState.RUNNING, AppState.PAUSED, AppState.ERROR, AppState.STOPPING}:
            self.stop(reason="shutdown")

    def poll_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events

    def list_profiles(self) -> list[str]:
        return self._profile_store.list_names()

    def save_profile(self, name: str, connection: ConnectionConfig, session: SessionConfig) -> None:
        payload = {
            "connection": asdict(connection),
            "session": {
                **asdict(session),
                "save_dir": str(session.save_dir),
                "error_keywords": list(session.error_keywords),
            },
        }
        self._profile_store.save_profile(name, payload)

    def load_profile(self, name: str) -> tuple[ConnectionConfig, SessionConfig] | None:
        payload = self._profile_store.load_profile(name)
        if payload is None:
            return None

        connection_data = payload.get("connection", {})
        session_data = payload.get("session", {})
        connection = ConnectionConfig(**connection_data)
        session_data["save_dir"] = Path(session_data.get("save_dir", "."))
        session_data["error_keywords"] = tuple(
            session_data.get(
                "error_keywords",
                ["ERROR", "ERR", "FATAL", "CRITICAL", "EXCEPTION", "FAIL", "NG"],
            )
        )
        session = SessionConfig(**session_data)
        return connection, session

    def delete_profile(self, name: str) -> None:
        self._profile_store.delete_profile(name)

    def load_recovery_marker(self) -> dict[str, Any] | None:
        return self._recovery_store.load_marker()

    def clear_recovery_marker(self) -> None:
        self._recovery_store.clear_marker()

    def _normalize_session(self, session: SessionConfig) -> SessionConfig:
        return replace(session, error_keywords=normalize_error_keywords(session.error_keywords))

    def _write_recovery_marker(self) -> None:
        if self._connection is None or self._session is None:
            return

        payload = {
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "connection": asdict(self._connection),
            "session": {
                **asdict(self._session),
                "save_dir": str(self._session.save_dir),
                "error_keywords": list(self._session.error_keywords),
            },
            "session_dir": str(self._stats.session_dir) if self._stats.session_dir else "",
        }
        self._recovery_store.write_marker(payload)

    def _on_serial_open(self) -> None:
        self._emit_event({"type": "status", "message": "Serial port connected."})

    def _on_serial_line(self, line: str) -> None:
        timestamp = datetime.now()
        writer = self._writer
        session = self._session
        if writer is None or session is None:
            with self._lock:
                self._stats.dropped_lines += 1
            return

        marker = classify_log_line(line, session.error_keywords)
        is_error = marker.severity == "error"
        write_ok = writer.write_line(timestamp, line, is_error)

        with self._lock:
            self._stats.received_lines += 1
            if is_error:
                self._stats.error_lines += 1
            if not write_ok:
                self._stats.write_failures += 1
                self._stats.last_error = "Log write failed."

        self._emit_event(
            {
                "type": "line",
                "timestamp": timestamp.strftime("%H:%M:%S"),
                "line": line,
                "is_error": is_error,
                "severity": marker.severity,
                "marker_terms": list(marker.matched_terms),
                "write_ok": write_ok,
            }
        )

    def _on_serial_error(self, message: str) -> None:
        with self._lock:
            self._stats.last_error = message

        self._emit_event({"type": "error", "message": message})
        self.stop(reason="serial_error")

    def _on_serial_reconnect(self, attempt: int, max_retries: int, delay_sec: float, detail: str) -> None:
        event = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "attempt": str(attempt),
            "max_retries": str(max_retries),
            "delay_sec": f"{delay_sec:.2f}",
            "detail": detail,
        }
        with self._lock:
            self._stats.reconnect_attempts += 1
            self._stats.reconnect_events.append(event)

        self._emit_event(
            {
                "type": "status",
                "message": (
                    f"Reconnect attempt {attempt}/{max_retries} in {delay_sec:.1f}s: {detail}"
                ),
            }
        )

    def _move_state(self, to_state: AppState) -> None:
        if self.state == to_state:
            return
        self._state_machine.transition(to_state)
        self._emit_event({"type": "state", "state": to_state.value})

    def _emit_event(self, event: dict[str, Any]) -> None:
        try:
            self._events.put_nowait(event)
        except queue.Full:
            if event.get("type") == "line":
                with self._lock:
                    self._stats.dropped_lines += 1
