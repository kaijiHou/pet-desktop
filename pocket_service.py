"""Reference-only Pocket storage for files and directories."""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from paths import DATA_DIR


LOGGER = logging.getLogger("pet.pocket")
POCKET_FILE = DATA_DIR / "pocket.json"


@dataclass(frozen=True)
class PocketItem:
    """A reference to an existing file-system item; never a copied payload."""

    id: str
    path: Path
    name: str
    item_type: str
    added_at: datetime

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": str(self.path),
            "name": self.name,
            "item_type": self.item_type,
            "added_at": self.added_at.isoformat(timespec="seconds"),
        }


class PocketService:
    """Persist and validate references without modifying their targets."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        now_provider: Optional[Callable[[], datetime]] = None,
    ):
        self.storage_path = Path(storage_path) if storage_path else POCKET_FILE
        self._now = now_provider or datetime.now
        self._items = self._load()

    def add(self, path: Path) -> PocketItem:
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(resolved)

        canonical = self._canonical_path(resolved)
        existing = next(
            (item for item in self._items if self._canonical_path(item.path) == canonical),
            None,
        )
        if existing:
            return existing

        item = PocketItem(
            id=uuid4().hex,
            path=resolved,
            name=resolved.name or str(resolved),
            item_type="directory" if resolved.is_dir() else "file",
            added_at=self._now().replace(microsecond=0),
        )
        self._items.append(item)
        self._save()
        LOGGER.info("Pocket reference added id=%s type=%s path=%s", item.id, item.item_type, item.path)
        return item

    def list_items(self, include_missing: bool = True) -> list[PocketItem]:
        items = self._items if include_missing else [item for item in self._items if item.exists]
        return list(sorted(items, key=lambda item: item.added_at))

    def get(self, item_id: str) -> Optional[PocketItem]:
        return next((item for item in self._items if item.id == item_id), None)

    def remove(self, item_id: str) -> bool:
        original_count = len(self._items)
        self._items = [item for item in self._items if item.id != item_id]
        if len(self._items) == original_count:
            return False
        self._save()
        LOGGER.info("Pocket reference removed id=%s", item_id)
        return True

    def cleanup_missing(self) -> list[PocketItem]:
        missing = [item for item in self._items if not item.exists]
        if missing:
            missing_ids = {item.id for item in missing}
            self._items = [item for item in self._items if item.id not in missing_ids]
            self._save()
            LOGGER.info("Pocket invalid references cleaned count=%s", len(missing))
        return missing

    @staticmethod
    def _canonical_path(path: Path) -> str:
        return str(path).casefold()

    def _load(self) -> list[PocketItem]:
        if not self.storage_path.exists():
            return []
        try:
            raw_items = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if not isinstance(raw_items, list):
                return []
        except (OSError, json.JSONDecodeError):
            LOGGER.warning("Could not read Pocket storage; starting empty")
            return []

        items = []
        seen_paths = set()
        for raw in raw_items:
            try:
                item_type = str(raw["item_type"])
                if item_type not in {"file", "directory"}:
                    raise ValueError
                path = Path(raw["path"]).expanduser().resolve()
                item = PocketItem(
                    id=str(raw["id"]),
                    path=path,
                    name=str(raw["name"]),
                    item_type=item_type,
                    added_at=datetime.fromisoformat(raw["added_at"]),
                )
                if not item.id or not item.name:
                    raise ValueError
                canonical = self._canonical_path(path)
                if canonical in seen_paths:
                    continue
                seen_paths.add(canonical)
                items.append(item)
            except (KeyError, TypeError, ValueError):
                LOGGER.warning("Skipping invalid Pocket entry")
        return items

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps([item.to_dict() for item in self._items], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.storage_path)
