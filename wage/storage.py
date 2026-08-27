"""Small atomic JSON persistence helpers for wage data."""

import json
import logging
from pathlib import Path

LOGGER = logging.getLogger("pet.wage")


def load_json(path: Path, default):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return raw
    except (OSError, ValueError, TypeError):
        return default


def save_json_atomic(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)

