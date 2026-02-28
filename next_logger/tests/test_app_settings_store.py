from pathlib import Path
import tempfile
import unittest

from next_logger.infrastructure.app_settings_store import AppSettingsStore


class TestAppSettingsStore(unittest.TestCase):
    def test_bool_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AppSettingsStore(path=Path(tmp) / "settings.json")
            self.assertFalse(store.get_bool("onboarding_completed", default=False))
            store.set_bool("onboarding_completed", True)
            self.assertTrue(store.get_bool("onboarding_completed", default=False))


if __name__ == "__main__":
    unittest.main()
