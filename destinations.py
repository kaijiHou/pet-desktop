"""Persistent favorite destinations for Pocket file operations."""

from dataclasses import dataclass, replace
from datetime import datetime
import json
import logging
from pathlib import Path
from uuid import uuid4

from paths import DATA_DIR


DESTINATIONS_FILE = DATA_DIR / "destinations.json"
MAX_FAVORITES = 20
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FavoriteDestination:
    id: str
    path: Path
    name: str
    added_at: datetime
    order: int = 0

    @property
    def exists(self):
        return self.path.is_dir()

    def to_dict(self):
        return {"id": self.id, "path": str(self.path), "name": self.name,
                "added_at": self.added_at.isoformat(timespec="seconds"), "order": self.order}


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
            uuid4().hex, resolved, display_default_name(resolved), datetime.now().replace(microsecond=0)
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
        if len(self._favorites) >= MAX_FAVORITES:
            raise ValueError(f"最多只能添加 {MAX_FAVORITES} 个常用文件夹")
        item = FavoriteDestination(
            uuid4().hex, resolved, display_default_name(resolved),
            datetime.now().replace(microsecond=0), len(self._favorites),
        )
        self._favorites.append(item)
        self._save()
        return item

    def remove_favorite(self, favorite_id):
        before = len(self._favorites)
        self._favorites = [item for item in self._favorites if item.id != favorite_id]
        if len(self._favorites) == before:
            return False
        self._normalize_orders()
        self._save()
        return True

    def rename_favorite(self, favorite_id, new_name):
        name = str(new_name).strip()
        if not name or len(name) > 40:
            raise ValueError("名称必须为 1 到 40 个字符")
        index = next((i for i, item in enumerate(self._favorites) if item.id == favorite_id), None)
        if index is None:
            return None
        self._favorites[index] = replace(self._favorites[index], name=name)
        self._save()
        return self._favorites[index]

    def update_favorite_path(self, favorite_id, new_path):
        resolved = Path(new_path).expanduser().resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        index = next((i for i, item in enumerate(self._favorites) if item.id == favorite_id), None)
        if index is None:
            return None
        key = str(resolved).casefold()
        if any(i != index and str(item.path).casefold() == key
               for i, item in enumerate(self._favorites)):
            raise ValueError("该文件夹已经添加为常用文件夹")
        self._favorites[index] = replace(self._favorites[index], path=resolved)
        self._save()
        return self._favorites[index]

    def reorder_favorites(self, ordered_ids):
        ordered_ids = list(ordered_ids)
        current_ids = [item.id for item in self._favorites]
        if (len(ordered_ids) != len(current_ids) or len(set(ordered_ids)) != len(ordered_ids)
                or set(ordered_ids) != set(current_ids)):
            raise ValueError("排序必须包含每个常用文件夹 ID，且不能重复")
        by_id = {item.id: item for item in self._favorites}
        self._favorites = [replace(by_id[item_id], order=index)
                           for index, item_id in enumerate(ordered_ids)]
        self._save()
        return self.list_favorites()

    def _normalize_orders(self):
        self._favorites = [replace(item, order=index)
                           for index, item in enumerate(self._favorites)]

    def _load(self):
        if not self.storage_path.exists():
            return [], []
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("destination data must be an object")
            favorites = data.get("favorites", [])
            recents = data.get("recents", [])
            version = data.get("version", 1)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            LOGGER.warning("Could not load destinations from %s; preserving the original file: %s",
                           self.storage_path, exc)
            self._backup_corrupt_file()
            return [], []
        favorite_items = self._parse_items(favorites, preserve_order=version != 1)
        favorite_items.sort(key=lambda item: item.order)
        favorite_items = [replace(item, order=index) for index, item in enumerate(favorite_items)]
        recent_items = self._parse_items(recents)[:10]
        return favorite_items, recent_items

    @staticmethod
    def _parse_items(raw_items, preserve_order=True):
        result = []
        if not isinstance(raw_items, list):
            return result
        for index, raw in enumerate(raw_items):
            try:
                result.append(FavoriteDestination(str(raw["id"]), Path(raw["path"]).resolve(),
                                                  str(raw["name"]), datetime.fromisoformat(raw["added_at"]),
                                                  int(raw.get("order", index)) if preserve_order else index))
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def _backup_corrupt_file(self):
        try:
            raw = self.storage_path.read_bytes()
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = self.storage_path.with_name(f"{self.storage_path.name}.corrupt-{stamp}.bak")
            with backup.open("xb") as stream:
                stream.write(raw)
            LOGGER.warning("Preserved corrupt destination data at %s", backup)
        except OSError:
            LOGGER.exception("Could not back up corrupt destination data at %s", self.storage_path)

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temporary.write_text(json.dumps({
            "version": 2,
            "favorites": [item.to_dict() for item in self._favorites],
            "recents": [item.to_dict() for item in self._recents],
        },
                                        indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.storage_path)


def display_default_name(path):
    """Return a friendly default name, including roots such as D:\\ -> D盘."""
    path = Path(path)
    if path.drive and path == Path(path.anchor):
        drive = path.drive.rstrip(":")
        if len(drive) == 1 and drive.isalpha():
            return f"{drive.upper()}盘"
    return path.name or str(path)
