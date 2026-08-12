"""Persistent favorite destinations for Pocket file operations."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from paths import DATA_DIR


DESTINATIONS_FILE = DATA_DIR / "destinations.json"


@dataclass(frozen=True)
class FavoriteDestination:
    id: str
    path: Path
    name: str
    added_at: datetime

    @property
    def exists(self):
        return self.path.is_dir()

    def to_dict(self):
        return {"id": self.id, "path": str(self.path), "name": self.name,
                "added_at": self.added_at.isoformat(timespec="seconds")}


class DestinationService:
    def __init__(self, storage_path=None):
        self.storage_path = Path(storage_path) if storage_path else DESTINATIONS_FILE
        self._favorites, self._recents = self._load()

    def list_favorites(self):
        return list(self._favorites)

    def get_favorite(self, favorite_id):
        return next((item for item in self._favorites if item.id == favorite_id), None)

    def list_recents(self):
        return list(self._recents)

    def get_recent(self, recent_id):
        return next((item for item in self._recents if item.id == recent_id), None)

    def record_recent(self, path):
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        key = str(resolved).casefold()
        existing = next((item for item in self._recents if str(item.path).casefold() == key), None)
        item = existing or FavoriteDestination(
            uuid4().hex, resolved, resolved.name or str(resolved), datetime.now().replace(microsecond=0)
        )
        self._recents = [item] + [entry for entry in self._recents if entry.id != item.id]
        self._recents = self._recents[:10]
        self._save()
        return item

    def clear_recents(self):
        if not self._recents:
            return
        self._recents = []
        self._save()

    def add_favorite(self, path):
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        key = str(resolved).casefold()
        existing = next((item for item in self._favorites if str(item.path).casefold() == key), None)
        if existing:
            return existing
        item = FavoriteDestination(uuid4().hex, resolved, resolved.name or str(resolved), datetime.now().replace(microsecond=0))
        self._favorites.append(item)
        self._save()
        return item

    def remove_favorite(self, favorite_id):
        before = len(self._favorites)
        self._favorites = [item for item in self._favorites if item.id != favorite_id]
        if len(self._favorites) == before:
            return False
        self._save()
        return True

    def _load(self):
        if not self.storage_path.exists():
            return [], []
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            favorites = data.get("favorites", []) if isinstance(data, dict) else []
            recents = data.get("recents", []) if isinstance(data, dict) else []
        except (OSError, json.JSONDecodeError):
            return [], []
        return self._parse_items(favorites), self._parse_items(recents)[:10]

    @staticmethod
    def _parse_items(raw_items):
        result = []
        for raw in raw_items:
            try:
                result.append(FavoriteDestination(str(raw["id"]), Path(raw["path"]).resolve(),
                                                  str(raw["name"]), datetime.fromisoformat(raw["added_at"])))
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temporary.write_text(json.dumps({
            "favorites": [item.to_dict() for item in self._favorites],
            "recents": [item.to_dict() for item in self._recents],
        },
                                        indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.storage_path)
