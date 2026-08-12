#!/usr/bin/env python3
"""
📎 Clippy Desktop Pet — WebEngine Edition
Uses clippyjs via HTML5 Canvas for smooth pixel-perfect rendering.

Usage:
  python main.py

Phase 2: this entry wrapper now initializes application logging and records
the core lifecycle (startup, exit, uncaught startup exception). Behavior is
preserved — any exception is logged and then re-raised unchanged, so the
process exit code matches the upstream behavior exactly. Business code
(pet_window_web.py) is untouched.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pet_window_web import main

# Logging infrastructure (Phase 2). Import is safe even before the GUI.
import applog


def _run():
    log = applog.setup_logging()
    log.info("startup: pet-desktop launching (python %s)", sys.version.split()[0])
    try:
        code = main()
    except Exception:
        # Uncaught startup/runtime exception: record it, then re-raise so the
        # exit behavior is identical to the original unwrapped entry point.
        log.exception("startup: uncaught exception")
        raise
    log.info("exit: pet-desktop terminated normally (code=%s)", code)
    return code


if __name__ == "__main__":
    sys.exit(_run())
