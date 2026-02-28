import unittest

from next_logger.infrastructure.serial_worker import compute_backoff_delay


class TestBackoffDelay(unittest.TestCase):
    def test_fixed_delay(self) -> None:
        self.assertEqual(compute_backoff_delay(2.0, attempt=1, mode="fixed", max_interval_sec=10.0), 2.0)
        self.assertEqual(compute_backoff_delay(2.0, attempt=5, mode="fixed", max_interval_sec=10.0), 2.0)

    def test_exponential_delay_with_cap(self) -> None:
        self.assertEqual(compute_backoff_delay(1.0, attempt=1, mode="exponential", max_interval_sec=10.0), 1.0)
        self.assertEqual(compute_backoff_delay(1.0, attempt=2, mode="exponential", max_interval_sec=10.0), 2.0)
        self.assertEqual(compute_backoff_delay(1.0, attempt=5, mode="exponential", max_interval_sec=10.0), 10.0)


if __name__ == "__main__":
    unittest.main()
