from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
import re


DEFAULT_CUSTOM_ERROR_KEYWORDS: tuple[str, ...] = (
    "ERROR",
    "ERR",
    "FATAL",
    "CRITICAL",
    "EXCEPTION",
    "FAIL",
    "NG",
)

# RFC 5424 syslog + common application/framework conventions.
STANDARD_ERROR_KEYWORDS: tuple[str, ...] = (
    "emerg",
    "emergency",
    "alert",
    "crit",
    "critical",
    "fatal",
    "panic",
    "error",
    "err",
    "exception",
    "traceback",
    "stacktrace",
    "assertion failed",
    "segfault",
    "segmentation fault",
    "core dumped",
    "abort",
    "failed",
    "failure",
    "fault",
    "crash",
    "corrupt",
    "access denied",
    "permission denied",
    "connection refused",
    "unreachable",
    "broken pipe",
)

STANDARD_WARNING_KEYWORDS: tuple[str, ...] = (
    "warning",
    "warn",
    "caution",
    "deprecated",
    "deprecation",
    "notice",
    "retry",
    "reconnect",
    "timeout",
    "timed out",
    "unstable",
    "slow response",
    "latency",
    "queue full",
    "dropped",
    "drop",
    "throttle",
    "rate limit",
    "checksum mismatch",
    "overflow",
    "underflow",
)

_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bno\s+errors?\b", re.IGNORECASE),
    re.compile(r"\bwithout\s+errors?\b", re.IGNORECASE),
    re.compile(r"\berrors?\s*[:=]\s*0\b", re.IGNORECASE),
    re.compile(r"\berr\s*[:=]\s*0\b", re.IGNORECASE),
    re.compile(r"\bwarnings?\s*[:=]\s*0\b", re.IGNORECASE),
)

_ERROR_REGEX_PATTERNS: tuple[tuple[str, str], ...] = (
    ("traceback", r"\btraceback\s*\("),
    ("stacktrace", r"\bstack\s*trace\b"),
    ("signal_fault", r"\bsig(?:abrt|segv|bus)\b"),
    ("http_5xx", r"\b(?:http(?:_status)?|status|code)\s*[:= ]\s*5\d\d\b"),
    ("error_code", r"\b(?:e|err|error|fatal|panic)[-_]?\d{2,5}\b"),
)

_WARNING_REGEX_PATTERNS: tuple[tuple[str, str], ...] = (
    ("http_4xx", r"\b(?:http(?:_status)?|status|code)\s*[:= ]\s*4\d\d\b"),
    ("warning_code", r"\b(?:warn|warning|caution|notice)[-_]?\d{2,5}\b"),
)


@dataclass(frozen=True)
class LogMarkerResult:
    severity: str
    matched_terms: tuple[str, ...]


def _compile_word_patterns(tokens: Iterable[str]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for token in tokens:
        normalized = token.strip().lower()
        if not normalized:
            continue
        escaped = re.escape(normalized)
        pattern = re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)
        patterns.append((token.strip(), pattern))
    return tuple(patterns)


_STANDARD_ERROR_PATTERNS = _compile_word_patterns(STANDARD_ERROR_KEYWORDS)
_STANDARD_WARNING_PATTERNS = _compile_word_patterns(STANDARD_WARNING_KEYWORDS)
_ERROR_REGEX = tuple((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _ERROR_REGEX_PATTERNS)
_WARNING_REGEX = tuple((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _WARNING_REGEX_PATTERNS)


@lru_cache(maxsize=128)
def _compile_custom_error_patterns(tokens: tuple[str, ...]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    return _compile_word_patterns(tokens)


def _strip_noise(line: str) -> str:
    cleaned = line
    for pattern in _NOISE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


def _match_terms(line: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> list[str]:
    matched: list[str] = []
    for term, pattern in patterns:
        if pattern.search(line):
            matched.append(term)
    return matched


def _normalize_custom_keywords(keywords: Iterable[str]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in keywords:
        token = item.strip()
        folded = token.casefold()
        if not token or folded in seen:
            continue
        seen.add(folded)
        unique.append(token)
    return tuple(unique)


def classify_log_line(line: str, custom_error_keywords: Iterable[str] = ()) -> LogMarkerResult:
    prepared = _strip_noise(line)
    custom_keywords = _normalize_custom_keywords(custom_error_keywords)

    error_matches = []
    error_matches.extend(_match_terms(prepared, _STANDARD_ERROR_PATTERNS))
    error_matches.extend(_match_terms(prepared, _ERROR_REGEX))
    if custom_keywords:
        error_matches.extend(_match_terms(prepared, _compile_custom_error_patterns(custom_keywords)))

    if error_matches:
        unique = tuple(dict.fromkeys(error_matches))
        return LogMarkerResult(severity="error", matched_terms=unique)

    warning_matches = []
    warning_matches.extend(_match_terms(prepared, _STANDARD_WARNING_PATTERNS))
    warning_matches.extend(_match_terms(prepared, _WARNING_REGEX))
    if warning_matches:
        unique = tuple(dict.fromkeys(warning_matches))
        return LogMarkerResult(severity="warning", matched_terms=unique)

    return LogMarkerResult(severity="info", matched_terms=())
