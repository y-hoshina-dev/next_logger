import json
from pathlib import Path
import tempfile
import unittest

from next_logger.domain import ConnectionConfig, SessionConfig, SessionStats
from next_logger.infrastructure.log_writer import SessionLogWriter


class TestSessionLogWriter(unittest.TestCase):
    def test_manifest_contains_reconnect_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = SessionConfig(save_dir=Path(tmp), log_format="txt")
            writer = SessionLogWriter(config)
            connection = ConnectionConfig(
                port="COM9",
                baudrate=115200,
                reconnect_backoff_mode="exponential",
                reconnect_interval_sec=1.0,
                reconnect_max_interval_sec=8.0,
            )
            stats = SessionStats(
                received_lines=3,
                reconnect_attempts=2,
                reconnect_events=[
                    {"time": "2026-01-01T00:00:00", "attempt": "1", "detail": "open failed"},
                    {"time": "2026-01-01T00:00:02", "attempt": "2", "detail": "read failed"},
                ],
            )
            manifest = writer.close(status="stopped", stats=stats, reason="unit_test", connection=connection)
            payload = json.loads(Path(manifest).read_text(encoding="utf-8"))

            self.assertEqual(payload["stats"]["reconnect_attempts"], 2)
            self.assertEqual(len(payload["stats"]["reconnect_events"]), 2)
            self.assertEqual(payload["connection"]["port"], "COM9")
            self.assertEqual(payload["connection"]["reconnect_backoff_mode"], "exponential")


if __name__ == "__main__":
    unittest.main()
