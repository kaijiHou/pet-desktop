"""Codex Pet Manifest — loads and validates pet.json from Codex/Petdex packs.

Codex V1/V2 format:
    pet.json: {id, displayName, description, spritesheetPath, spriteVersionNumber}
    spritesheet.webp (or .png): 8-column grid, 192×208 cells

V1: 1536×1872 = 8×9
V2: 1536×2288 = 8×11
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger("pet.character_v4.manifest")

# ── Codex sprite row definitions (Microsoft Learn: Codex Desktop Pet) ─────
# V1 rows (0-8):
CODEX_V1_ROWS = {
    "idle":         (0, 6),   # row 0, 6 frames
    "running_r":    (1, 8),   # row 1, 8 frames
    "running_l":    (2, 8),   # row 2, 8 frames
    "waving":       (3, 4),   # row 3, 4 frames
    "jumping":      (4, 5),   # row 4, 5 frames
    "failed":       (5, 8),   # row 5, 8 frames
    "waiting":      (6, 6),   # row 6, 6 frames
    "running":      (7, 6),   # row 7, 6 frames
    "review":       (8, 6),   # row 8, 6 frames
}

# V2 rows (0-10) — V1 + look-up/look-down:
CODEX_V2_ROWS = {
    **CODEX_V1_ROWS,
    "look_up":      (9, 4),   # row 9
    "look_down":    (10, 4),  # row 10
}

# Cell size is always 192×208 for both V1 and V2
CODEX_CELL_W = 192
CODEX_CELL_H = 208

# Expected atlas dimensions
CODEX_V1_SIZE = (1536, 1872)  # 8×9 cells
CODEX_V2_SIZE = (1536, 2288)  # 8×11 cells


@dataclass
class ValidationResult:
    """Result of validating a Codex pet pack."""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


@dataclass
class CodexPetManifest:
    """Parsed Codex pet.json manifest."""
    id: str
    display_name: str
    description: str = ""
    spritesheet_path: str = "spritesheet.webp"
    sprite_version: int = 1
    source_path: Optional[Path] = None  # pack root

    @classmethod
    def from_dict(cls, data: dict) -> "CodexPetManifest":
        return cls(
            id=data.get("id", "unknown"),
            display_name=data.get("displayName", data.get("id", "Unknown")),
            description=data.get("description", ""),
            spritesheet_path=data.get("spritesheetPath", "spritesheet.webp"),
            sprite_version=data.get("spriteVersionNumber", 1),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "displayName": self.display_name,
            "description": self.description,
            "spritesheetPath": self.spritesheet_path,
            "spriteVersionNumber": self.sprite_version,
        }

    @classmethod
    def load(cls, pack_root: Path) -> "CodexPetManifest":
        """Load pet.json from a pack directory."""
        pet_json = pack_root / "pet.json"
        if not pet_json.exists():
            raise FileNotFoundError(f"pet.json not found in {pack_root}")
        with open(pet_json, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        manifest = cls.from_dict(data)
        manifest.source_path = pack_root
        return manifest

    def validate(self, pack_root: Optional[Path] = None) -> ValidationResult:
        """Validate the manifest and its spritesheet."""
        result = ValidationResult()
        pack_root = pack_root or self.source_path
        if not pack_root:
            result.errors.append("No pack root specified")
            return result

        # Check required fields
        if not self.id:
            result.errors.append("Missing 'id' field")
        elif not all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in self.id):
            result.errors.append(f"Invalid id characters: {self.id}")
        elif len(self.id) > 64:
            result.errors.append(f"id too long: {len(self.id)} (max 64)")

        # Check spritesheet path safety
        sheet_path = (pack_root / self.spritesheet_path).resolve()
        if not str(sheet_path).startswith(str(pack_root.resolve())):
            result.errors.append(f"Spritesheet path escapes pack root: {self.spritesheet_path}")
            return result
        if not sheet_path.exists():
            result.errors.append(f"Spritesheet not found: {self.spritesheet_path}")
            return result

        # Validate image dimensions
        try:
            from PIL import Image
            img = Image.open(sheet_path)
            w, h = img.size
            expected = CODEX_V2_SIZE if self.sprite_version == 2 else CODEX_V1_SIZE
            if (w, h) != expected:
                result.errors.append(
                    f"Atlas size {w}×{h} doesn't match V{self.sprite_version} "
                    f"expected {expected[0]}×{expected[1]}"
                )
            # Check grid
            cols = w // CODEX_CELL_W
            rows = h // CODEX_CELL_H
            expected_rows = 11 if self.sprite_version == 2 else 9
            if cols != 8:
                result.errors.append(f"Expected 8 columns, got {cols}")
            if rows != expected_rows:
                result.errors.append(f"Expected {expected_rows} rows, got {rows}")
        except Exception as exc:
            result.errors.append(f"Cannot read spritesheet: {exc}")

        return result

    def get_row_def(self, animation_name: str) -> Optional[tuple[int, int]]:
        """Get (row_index, frame_count) for an animation name."""
        rows = CODEX_V2_ROWS if self.sprite_version == 2 else CODEX_V1_ROWS
        return rows.get(animation_name)
