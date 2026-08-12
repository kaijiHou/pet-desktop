"""
Application logging setup (Phase 2 infrastructure).

Deliberately simple: stdlib logging + RotatingFileHandler. No framework.

Design constraints honored:
  * Log dir defaults to paths.LOG_DIR (project-local, D: in this workspace);
    callers may override (tests point it at temp dirs).
  * Directory auto-created on first use.
  * If the log file cannot be created, the app MUST NOT crash — fall back to
    stderr-only logging and report the reason once.
  * Rotation: 2 MB per file, 3 backups (small tool, low write volume).
    Chosen because the app logs only lifecycle events (Phase 2 scope), so a
    few MB of history is ample while keeping disk use bounded.
  * setup_logging is idempotent (safe to call more than once).

NOT wired into per-frame / per-tick / paint code paths — logging high-volume
GUI events would violate the low-resource goal.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from paths import LOG_DIR

LOG_NAME = "pet"
LOG_FILE_NAME = "app.log"
MAX_BYTES = 2 * 1024 * 1024  # 2 MB per file
BACKUP_COUNT = 3


def setup_logging(log_dir=None, level=logging.INFO):
    """Initialize the application logger; returns the configured Logger.

    log_dir: override target directory (used by tests). Defaults to LOG_DIR.
    """
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(level)

    # Idempotent: don't stack handlers on repeated calls.
    if any(isinstance(h, RotatingFileHandler) for h in logger.handlers) or any(
        isinstance(h, logging.StreamHandler) for h in logger.handlers
    ):
        return logger

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    target_dir = log_dir if log_dir is not None else LOG_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            target_dir / LOG_FILE_NAME,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except OSError as e:
        # Fallback: stderr only. The application must keep working.
        logger.warning("logging: cannot open log file in %s (%s); using stderr only", target_dir, e)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)
    logger.addHandler(stderr_handler)

    return logger
