r"""Tests for the applog logging infrastructure (Phase 2).

All log output is redirected into per-test temp dirs under D:\pet-desktop\.tmp\tests\ —
the real logs/app.log is never touched by tests.
"""

import logging

import pytest

import applog
from paths import LOG_DIR


@pytest.fixture
def clean_logger():
    """Isolate the global 'pet' logger: strip handlers before, restore after."""
    logger = logging.getLogger(applog.LOG_NAME)
    saved = list(logger.handlers)
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    yield logger
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    for h in saved:
        logger.addHandler(h)


@pytest.mark.unit
class TestSetupLogging:
    def test_returns_named_logger(self, clean_logger, test_temp_root):
        logger = applog.setup_logging(log_dir=test_temp_root)
        assert logger is clean_logger
        assert logger.name == applog.LOG_NAME

    def test_log_directory_is_created_when_missing(self, clean_logger, test_temp_root):
        target = test_temp_root / "new" / "nested" / "logs"
        assert not target.exists()

        applog.setup_logging(log_dir=target)

        assert target.is_dir()

    def test_log_file_is_created_and_message_written(self, clean_logger, test_temp_root):
        logger = applog.setup_logging(log_dir=test_temp_root)

        logger.info("hello-from-test")
        for h in logger.handlers:
            h.flush()

        content = (test_temp_root / applog.LOG_FILE_NAME).read_text(encoding="utf-8")
        assert "hello-from-test" in content
        assert "INFO" in content

    def test_rotation_handler_configured_with_bounds(self, clean_logger, test_temp_root):
        logger = applog.setup_logging(log_dir=test_temp_root)

        rotating = [h for h in logger.handlers
                    if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(rotating) == 1
        assert rotating[0].maxBytes == applog.MAX_BYTES
        assert rotating[0].backupCount == applog.BACKUP_COUNT

    def test_setup_is_idempotent_no_handler_stacking(self, clean_logger, test_temp_root):
        applog.setup_logging(log_dir=test_temp_root)
        n_after_first = len(clean_logger.handlers)

        applog.setup_logging(log_dir=test_temp_root)

        assert len(clean_logger.handlers) == n_after_first

    def test_unwritable_dir_falls_back_without_raising(self, clean_logger, test_temp_root):
        # Arrange: a FILE where the log DIR should be -> mkdir raises OSError.
        blocker = test_temp_root / "blocker"
        blocker.write_text("i am a file")

        logger = applog.setup_logging(log_dir=blocker)  # must not raise

        # Fallback: stderr handler only, no file handler.
        assert not any(isinstance(h, logging.handlers.RotatingFileHandler)
                       for h in logger.handlers)
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


@pytest.mark.unit
class TestLoggingDefaults:
    def test_default_log_dir_is_project_logs(self):
        assert LOG_DIR.name == "logs"
        assert LOG_DIR.parent.name == "pet-desktop"

    def test_log_file_name_is_app_log(self):
        assert applog.LOG_FILE_NAME == "app.log"

    def test_rotation_bounds_are_small_tool_sized(self):
        # Rationale recorded in applog.py: small lifecycle-only logging.
        assert 1 * 1024 * 1024 <= applog.MAX_BYTES <= 10 * 1024 * 1024
        assert 1 <= applog.BACKUP_COUNT <= 5
