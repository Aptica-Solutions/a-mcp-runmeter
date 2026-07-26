"""
Structured JSON logger for tooling scripts and project Python code.

Lives in _engineer/dev-env/. Because the directory name contains a
hyphen, use sys.path to import rather than dotted package syntax:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dev-env"))
    from log_util import get_logger

    log = get_logger(__name__)
    log.info("Processing file", extra={"file": path, "correlation_id": cid})

Scripts that already live in dev-env/ can import directly:

    from log_util import get_logger

Reads from env:
    LOG_LEVEL   - debug | info | warn | error  (default: info)
    LOG_FILE    - file path, or empty to log to stdout only
"""

import logging
import os
import sys
from pathlib import Path

try:
    from pythonjsonlogger import jsonlogger
    _JSON_AVAILABLE = True
except ImportError:
    _JSON_AVAILABLE = False

_configured = False


def _configure():
    global _configured
    if _configured:
        return

    level_name = os.getenv("LOG_LEVEL", "info").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"

    if _JSON_AVAILABLE:
        formatter = jsonlogger.JsonFormatter(fmt, rename_fields={"levelname": "level", "asctime": "timestamp"})
    else:
        formatter = logging.Formatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # File handler (optional)
    log_file = os.getenv("LOG_FILE", "").strip()
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(formatter)
        root.addHandler(fh)

    if not _JSON_AVAILABLE:
        logging.getLogger(__name__).warning(
            "python-json-logger not installed — falling back to plain text. "
            "Run: pip install python-json-logger"
        )

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Call once per module at import time."""
    _configure()
    return logging.getLogger(name)
