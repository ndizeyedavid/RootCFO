"""David: Audit log formatter — returns timestamped, severity-tagged strings."""

from datetime import datetime

LEVEL_LABELS = {
    "info": "INFO",
    "warn": "WARN",
    "warning": "WARN",
    "err": "CRIT",
    "error": "CRIT",
    "critical": "CRIT",
    "crit": "CRIT",
    "debug": "DEBUG",
}

DEFAULT_LEVEL = "INFO"
TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"


def log(message: str, level: str = "info") -> str:
    """Return a formatted audit log line like: [LEVEL] YYYY-MM-DD HH:MM:SS — message

    Args:
        message: the audit/event text to record.
        level: severity token. Normalized via LEVEL_LABELS; unknown values
               fall back to uppercase of the input.

    Returns:
        Single formatted string.
    """
    key = (level or "").lower()
    tag = LEVEL_LABELS.get(key, (level or DEFAULT_LEVEL).upper())
    stamp = datetime.now().strftime(TIMESTAMP_FMT)
    return f"[{tag}] {stamp} — {message}"