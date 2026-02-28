import unittest
from pathlib import Path
import tempfile

from next_logger.application.preflight import run_preflight, sanitize_component
from next_logger.domain import ConnectionConfig, SessionConfig


class TestSanitizeComponent(unittest.TestCase):
    def test_invalid_chars_are_replaced(self) -> None:
        value = 'ab:c*de?f"g<h>i|j'
        self.assertEqual(sanitize_component(value), "ab_c_de_f_g_h_i_j")

    def test_empty_falls_back(self) -> None:
        self.assertEqual(sanitize_component("   "), "na")

    def test_reserved_name_is_prefixed(self) -> None:
        self.assertEqual(sanitize_component("CON"), "_CON")


class TestPreflight(unittest.TestCase):
    def test_reconnect_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = ConnectionConfig(
                port="COM9",
                baudrate=9600,
                reconnect_max_retries=-1,
                reconnect_interval_sec=0.0,
            )
            session = SessionConfig(save_dir=Path(tmp))
            result = run_preflight(conn, session, available_ports=["COM9"])
            self.assertIn("再接続回数は0以上で指定してください。", result.errors)
            self.assertIn("再接続待機秒数は0より大きい値にしてください。", result.errors)

    def test_reconnect_backoff_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = ConnectionConfig(
                port="COM9",
                baudrate=9600,
                reconnect_backoff_mode="unknown",  # type: ignore[arg-type]
                reconnect_interval_sec=2.0,
                reconnect_max_interval_sec=1.0,
            )
            session = SessionConfig(save_dir=Path(tmp))
            result = run_preflight(conn, session, available_ports=["COM9"])
            self.assertIn("再接続モードは fixed / exponential のいずれかを選択してください。", result.errors)
            self.assertIn("再接続の最大待機秒数は基本待機秒数以上にしてください。", result.errors)

    def test_retention_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = ConnectionConfig(port="COM9", baudrate=9600)
            session = SessionConfig(
                save_dir=Path(tmp),
                retention_max_sessions=-1,
                retention_max_age_days=-1,
            )
            result = run_preflight(conn, session, available_ports=["COM9"])
            self.assertIn("保持セッション数は0以上で指定してください。", result.errors)
            self.assertIn("保持日数は0以上で指定してください。", result.errors)


if __name__ == "__main__":
    unittest.main()
