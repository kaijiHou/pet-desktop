"""Application build identity (V5.0).

Read-only at runtime: the build script writes build_info.json next to the
executable (and packs it via PyInstaller); we never invoke git at runtime
(frozen builds have no .git).

Source-tree runs fall back to APP_VERSION with git_sha="dev" when the file
has not been generated yet.
"""

import json
from pathlib import Path

APP_VERSION = "V5.0"

try:
    from paths import BUNDLE_ROOT as _ROOT
except ImportError:  # direct import before paths is unlikely; keep safe
    _ROOT = Path(__file__).resolve().parent


def build_info() -> dict:
    """Return {version, git_sha, build_time}; never crashes, never runs git."""
    for candidate in (_ROOT / "build_info.json", Path(__file__).resolve().parent / "build_info.json"):
        try:
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                return {
                    "version": str(raw.get("version", APP_VERSION)),
                    "git_sha": str(raw.get("git_sha", "unknown")),
                    "build_time": str(raw.get("build_time", "")),
                }
        except (OSError, ValueError):
            continue
    return {"version": APP_VERSION, "git_sha": "dev", "build_time": ""}


def display_id() -> str:
    """'V5.0 · abc1234' short form for logs and the Settings footer."""
    info = build_info()
    sha = info["git_sha"]
    short = sha[:7] if sha and sha not in ("dev", "unknown") else sha
    return f"{info['version']} · {short}" if short else info["version"]
