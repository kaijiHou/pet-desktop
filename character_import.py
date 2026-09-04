"""Portable single-image character import shared by Settings and Gallery."""
from pathlib import Path

from character import import_character_image


class SingleCharacterImportService:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.image_dir = self.data_dir / "character_images"

    def import_image(self, source):
        name = import_character_image(Path(source), self.image_dir)
        return self.image_dir / name

    def relative_path(self, path):
        path = Path(path)
        if not path.is_absolute() and path.as_posix().startswith("character_images/"):
            return path.as_posix()
        try:
            return path.resolve().relative_to(self.data_dir.resolve()).as_posix()
        except ValueError:
            return path.name

    def resolve(self, stored):
        if not stored:
            return None
        path = Path(stored)
        if path.is_absolute() and path.exists():
            return path
        candidate = self.data_dir / stored
        if candidate.exists():
            return candidate
        candidate = self.image_dir / path.name
        if candidate.exists():
            return candidate
        # V2/V3 stored only the filename in the project assets directory.
        from paths import PROJECT_ROOT
        legacy = PROJECT_ROOT / "assets" / path.name
        return legacy if legacy.exists() else None
