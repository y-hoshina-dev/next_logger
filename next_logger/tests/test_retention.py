import unittest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from next_logger.infrastructure.retention import apply_retention_policy


class TestRetentionPolicy(unittest.TestCase):
    def _create_session_dir(self, base: Path, name: str, age_days: int) -> Path:
        path = base / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "manifest.json").write_text("{}", encoding="utf-8")
        stamp = (datetime.now() - timedelta(days=age_days)).timestamp()
        import os

        os.utime(path, (stamp, stamp))
        os.utime(path / "manifest.json", (stamp, stamp))
        return path

    def test_removes_by_age(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_dir = self._create_session_dir(base, "old", age_days=10)
            self._create_session_dir(base, "new", age_days=0)

            result = apply_retention_policy(base, max_sessions=0, max_age_days=3)

            self.assertEqual(result["removed_age"], 1)
            self.assertFalse(old_dir.exists())

    def test_removes_by_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            d1 = self._create_session_dir(base, "d1", age_days=0)
            d2 = self._create_session_dir(base, "d2", age_days=0)
            d3 = self._create_session_dir(base, "d3", age_days=0)

            # Force deterministic order: d3 newest, d2 middle, d1 oldest.
            import os

            now = datetime.now().timestamp()
            os.utime(d1, (now - 30, now - 30))
            os.utime(d2, (now - 20, now - 20))
            os.utime(d3, (now - 10, now - 10))

            result = apply_retention_policy(base, max_sessions=2, max_age_days=0)

            self.assertEqual(result["removed_count"], 1)
            self.assertFalse(d1.exists())
            self.assertTrue(d2.exists())
            self.assertTrue(d3.exists())

    def test_keep_dirs_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            keep = self._create_session_dir(base, "keep", age_days=10)
            self._create_session_dir(base, "drop", age_days=10)

            result = apply_retention_policy(base, max_sessions=0, max_age_days=1, keep_dirs={keep})

            self.assertEqual(result["removed_age"], 1)
            self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()
