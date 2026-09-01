"""Character Registry — manages built-in and user-installed character packs."""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .manifest import CodexPetManifest, ValidationResult

LOGGER = logging.getLogger("pet.character_v4.registry")

BUILTIN_ID = "default_dynamic_ghost"


@dataclass
class CharacterEntry:
    """A character available for selection."""
    id: str
    display_name: str
    description: str = ""
    source: str = "builtin"  # builtin / installed / codex
    pack_root: Optional[Path] = None
    is_builtin: bool = False


class CharacterRegistry:
    """Manages character pack discovery and lifecycle."""

    def __init__(self, assets_dir: Path, data_dir: Path):
        self._assets_dir = assets_dir
        self._data_dir = data_dir
        self._characters_dir = data_dir / "characters"
        self._characters_dir.mkdir(parents=True, exist_ok=True)

    def builtin(self) -> CharacterEntry:
        """Return the built-in dynamic ghost."""
        pack_dir = self._assets_dir / BUILTIN_ID
        try:
            m = CodexPetManifest.load(pack_dir)
            return CharacterEntry(
                id=m.id, display_name=m.display_name,
                description=m.description, source="builtin",
                pack_root=pack_dir, is_builtin=True,
            )
        except Exception:
            return CharacterEntry(
                id=BUILTIN_ID, display_name="小幽灵",
                description="内置动态角色", source="builtin",
                pack_root=pack_dir, is_builtin=True,
            )

    def installed(self) -> list[CharacterEntry]:
        """List user-installed dynamic packs."""
        entries = []
        if not self._characters_dir.exists():
            return entries
        for d in sorted(self._characters_dir.iterdir()):
            if not d.is_dir():
                continue
            pet_json = d / "pet.json"
            if not pet_json.exists():
                continue
            try:
                m = CodexPetManifest.load(d)
                entries.append(CharacterEntry(
                    id=m.id, display_name=m.display_name,
                    description=m.description, source="installed",
                    pack_root=d,
                ))
            except Exception:
                LOGGER.warning("Skipping invalid pack: %s", d)
        return entries

    def scan_codex_home(self) -> list[CharacterEntry]:
        """Read-only scan of ~/.codex/pets."""
        codex_pets = Path.home() / ".codex" / "pets"
        if not codex_pets.exists():
            return []
        entries = []
        for d in sorted(codex_pets.iterdir()):
            if not d.is_dir():
                continue
            pet_json = d / "pet.json"
            if not pet_json.exists():
                continue
            try:
                m = CodexPetManifest.load(d)
                entries.append(CharacterEntry(
                    id=m.id, display_name=m.display_name,
                    description=m.description, source="codex",
                    pack_root=d,
                ))
            except Exception:
                pass
        return entries

    def all(self) -> list[CharacterEntry]:
        """All available characters."""
        result = [self.builtin()]
        result.extend(self.installed())
        result.extend(self.scan_codex_home())
        return result

    def resolve(self, char_id: str) -> Optional[CharacterEntry]:
        """Resolve a character id to its entry."""
        if char_id == BUILTIN_ID:
            return self.builtin()
        for entry in self.installed() + self.scan_codex_home():
            if entry.id == char_id:
                return entry
        return None

    def install(self, source: Path, char_id: Optional[str] = None) -> Optional[CharacterEntry]:
        """Install a dynamic pack from folder or zip."""
        from .importer import import_codex_pack
        path, result = import_codex_pack(source, self._characters_dir, char_id)
        if path is None or not result.ok:
            LOGGER.error("Install failed: %s", result.errors)
            return None
        try:
            m = CodexPetManifest.load(path)
            return CharacterEntry(
                id=m.id, display_name=m.display_name,
                description=m.description, source="installed",
                pack_root=path,
            )
        except Exception:
            return None

    def remove(self, char_id: str) -> bool:
        """Remove an installed character pack."""
        if char_id == BUILTIN_ID:
            LOGGER.warning("Cannot remove built-in character")
            return False
        pack_dir = self._characters_dir / char_id
        if not pack_dir.exists():
            return False
        try:
            shutil.rmtree(pack_dir)
            LOGGER.info("Removed character: %s", char_id)
            return True
        except Exception:
            LOGGER.exception("Failed to remove character: %s", char_id)
            return False

    def pack_root(self, char_id: str) -> Optional[Path]:
        """Get the filesystem path for a character pack."""
        entry = self.resolve(char_id)
        return entry.pack_root if entry else None
