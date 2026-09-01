"""
Unified path constants for pet-desktop (Phase 2 infrastructure).

Purpose: give logging and test-temp code ONE place to resolve project paths,
instead of scattering absolute paths through the source tree.

Deliberately minimal — this does NOT migrate the user config system
(config.py still owns CONFIG_DIR for runtime state; that stays untouched).
"""

from pathlib import Path
import sys

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
else:
    PROJECT_ROOT = Path(__file__).resolve().parent
    BUNDLE_ROOT = PROJECT_ROOT

# Project-local directories (all on the project drive, D: in this workspace)
LOG_DIR = PROJECT_ROOT / "logs"
TEMP_DIR = PROJECT_ROOT / ".tmp"

# Runtime state stays beside the project/executable instead of silently
# consuming the system drive. It contains configuration and local indexes,
# never the user's referenced Pocket payloads.
ASSETS_DIR = BUNDLE_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = DATA_DIR
