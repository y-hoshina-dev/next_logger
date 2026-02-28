from __future__ import annotations

from collections.abc import Callable
import threading
import time

import serial

from next_logger.domain.models import ConnectionConfig


def compute_backoff_delay(
    base_interval_sec: float,
    attempt: int,
    mode: str,
    max_interval_sec: float,
) -> float:
    if attempt <= 0:
        return max(0.0, base_interval_sec)

    if mode == "exponential":
        delay = base_interval_sec * (2 ** (attempt - 1))
    else:
        delay = base_interval_sec

    return max(0.0, min(delay, max_interval_sec))


class SerialWorker(threading.Thread):
    def __init__(
        self,
        connection: ConnectionConfig,
        on_open: Callable[[], None],
        on_line: Callable[[str], None],
        on_error: Callable[[str], None],
        on_reconnect: Callable[[int, int, float, str], None],
    ) -> None:
        super().__init__(daemon=True)
        self._connection = connection
        self._on_open = on_open
        self._on_line = on_line
        self._on_error = on_error
        self._on_reconnect = on_reconnect

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    def stop(self) -> None:
        self._stop_event.set()

    def _wait_with_stop(self, seconds: float) -> bool:
        deadline = time.monotonic() + max(seconds, 0.0)
        while time.monotonic() < deadline:
            if self._stop_event.is_set():
                return False
            time.sleep(0.05)
        return True

    def _handle_retry_or_fail(self, retries: int, detail: str) -> tuple[bool, float]:
        if not self._connection.auto_reconnect:
            self._on_error(detail)
            return False, 0.0

        if retries > self._connection.reconnect_max_retries:
            self._on_error(
                f"{detail} (reconnect retries exceeded: {self._connection.reconnect_max_retries})"
            )
            return False, 0.0

        delay = compute_backoff_delay(
            base_interval_sec=self._connection.reconnect_interval_sec,
            attempt=retries,
            mode=self._connection.reconnect_backoff_mode,
            max_interval_sec=self._connection.reconnect_max_interval_sec,
        )
        self._on_reconnect(retries, self._connection.reconnect_max_retries, delay, detail)
        if not self._wait_with_stop(delay):
            return False, delay
        return True, delay

    def run(self) -> None:
        retries = 0

        while not self._stop_event.is_set():
            try:
                ser = serial.Serial(
                    port=self._connection.port,
                    baudrate=self._connection.baudrate,
                    timeout=self._connection.timeout,
                    parity=self._connection.parity,
                    bytesize=self._connection.bytesize,
                    stopbits=self._connection.stopbits,
                )
            except (serial.SerialException, ValueError) as exc:
                retries += 1
                ok, _ = self._handle_retry_or_fail(retries, f"serial open error: {exc}")
                if not ok:
                    return
                continue

            retries = 0
            with ser:
                self._on_open()
                while not self._stop_event.is_set():
                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        continue

                    try:
                        raw = ser.readline()
                    except serial.SerialException as exc:
                        retries += 1
                        ok, _ = self._handle_retry_or_fail(retries, f"serial read error: {exc}")
                        if not ok:
                            return
                        break

                    if not raw:
                        continue

                    line = raw.decode("utf-8", errors="ignore").strip()
                    if line:
                        self._on_line(line)
