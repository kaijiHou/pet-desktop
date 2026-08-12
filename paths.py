"""
Unified path constants for pet-desktop (Phase 2 infrastructure).

Purpose: give logging and test-temp code ONE place to resolve project paths,
instead of scattering absolute paths through the source tree.

Deliberately minimal — this does NOT migrate the user config system
(config.py still owns CONFIG_DIR for runtime state; that stays untouched).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Project-local directories (all on the project drive, D: in this workspace)
LOG_DIR = PROJECT_ROOT / "logs"
TEMP_DIR = PROJECT_ROOT / ".tmp"

# User runtime state (upstream fixed location — see docs/KNOWN_ISSUES.md).
# Kept here only so logging/tests have a named reference; business code
# continues to use config.CONFIG_DIR unchanged.
DATA_DIR = Path.home() / "desktop-pet"
CONFIG_DIR = DATA_DIR
