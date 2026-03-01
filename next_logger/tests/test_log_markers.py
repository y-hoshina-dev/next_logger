import unittest

from next_logger.application.log_markers import DEFAULT_CUSTOM_ERROR_KEYWORDS, classify_log_line
from next_logger.application.preflight import normalize_error_keywords


class TestLogMarkers(unittest.TestCase):
    def test_syslog_style_critical_is_error(self) -> None:
        result = classify_log_line("2026-03-01 [CRIT] sensor fault detected")
        self.assertEqual(result.severity, "error")
        self.assertTrue(result.matched_terms)

    def test_warning_terms_are_warning(self) -> None:
        result = classify_log_line("WARN: reconnect retry after timeout")
        self.assertEqual(result.severity, "warning")
        self.assertTrue(result.matched_terms)

    def test_negated_error_phrases_are_ignored(self) -> None:
        result = classify_log_line("self-check complete: no error, warnings=0")
        self.assertEqual(result.severity, "info")
        self.assertEqual(result.matched_terms, ())

    def test_custom_keywords_are_supported(self) -> None:
        result = classify_log_line("device entered NG state", custom_error_keywords=("NG",))
        self.assertEqual(result.severity, "error")
        self.assertIn("NG", result.matched_terms)

    def test_http_5xx_is_error(self) -> None:
        result = classify_log_line("request failed status=500")
        self.assertEqual(result.severity, "error")

    def test_default_keyword_normalization(self) -> None:
        self.assertEqual(normalize_error_keywords(""), DEFAULT_CUSTOM_ERROR_KEYWORDS)


if __name__ == "__main__":
    unittest.main()
