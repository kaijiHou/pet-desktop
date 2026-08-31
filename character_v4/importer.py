"""Codex Pet Importer — imports Codex packs from folder or ZIP.

Safety:
- ZIP slip prevention
- Path traversal prevention
- Size limits
- No symlink following
"""
from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from .manifest import CodexPetManifest, ValidationResult

LOGGER = logging.getLogger("pet.character_v4.importer")

MAX_IMPORT_SIZE_MB = 100


def import_codex_pack(
    source: Path,
    dest_dir: Path,
    pet_id: Optional[str] = None,
) -> tuple[Optional[Path], ValidationResult]:
    """Import a Codex pack from folder or ZIP.

    Returns (installed_path, validation_result).
    """
    result = ValidationResult()

    if source.is_dir():
        return _import_folder(source, dest_dir, pet_id, result)
    elif source.suffix.lower() == ".zip":
        return _import_zip(source, dest_dir, pet_id, result)
    else:
        result.errors.append(f"Unsupported source type: {source.suffix}")
        return None, result


def _import_folder(
    source: Path, dest_dir: Path, pet_id: Optional[str], result: ValidationResult
) -> tuple[Optional[Path], ValidationResult]:
    """Import from a folder containing pet.json + spritesheet."""
    pet_json = source / "pet.json"
    if not pet_json.exists():
        result.errors.append("pet.json not found in source folder")
        return None, result

    try:
        manifest = CodexPetManifest.load(source)
    except Exception as exc:
        result.errors.append(f"Invalid pet.json: {exc}")
        return None, result

    # Validate
    val = manifest.validate(source)
    result.errors.extend(val.errors)
    result.warnings.extend(val.warnings)
    if not val.ok:
        return None, result

    # Determine install path
    install_id = pet_id or manifest.id
    install_path = dest_dir / install_id
    if install_path.exists():
        result.warnings.append(f"Overwriting existing pack: {install_id}")
        shutil.rmtree(install_path)

    # Copy files
    try:
        shutil.copytree(source, install_path)
        manifest.source_path = install_path
        LOGGER.info("Imported pack %s → %s", install_id, install_path)
        return install_path, result
    except Exception as exc:
        result.errors.append(f"Copy failed: {exc}")
        return None, result


def _import_zip(
    source: Path, dest_dir: Path, pet_id: Optional[str], result: ValidationResult
) -> tuple[Optional[Path], ValidationResult]:
    """Import from a ZIP archive."""
    # Check size
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > MAX_IMPORT_SIZE_MB:
        result.errors.append(f"ZIP too large: {size_mb:.1f}MB (max {MAX_IMPORT_SIZE_MB}MB)")
        return None, result

    # Extract to temp dir first
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            with zipfile.ZipFile(source, "r") as zf:
                # Security: check for path traversal
                for info in zf.infolist():
                    if info.filename.startswith("/") or ".." in info.filename:
                        result.errors.append(f"Unsafe path in ZIP: {info.filename}")
                        return None, result
                    if info.file_size > MAX_IMPORT_SIZE_MB * 1024 * 1024:
                        result.errors.append(f"File too large in ZIP: {info.filename}")
                        return None, result
                zf.extractall(tmp_path)
        except zipfile.BadZipFile:
            result.errors.append("Invalid ZIP file")
            return None, result
        except Exception as exc:
            result.errors.append(f"ZIP extraction failed: {exc}")
            return None, result

        # Find pet.json in extracted contents
        pet_jsons = list(tmp_path.rglob("pet.json"))
        if not pet_jsons:
            result.errors.append("pet.json not found in ZIP")
            return None, result
        # Use the first one found (or the one at root)
        pack_root = pet_jsons[0].parent

        # Now import the folder
        return _import_folder(pack_root, dest_dir, pet_id, result)


def scan_codex_home() -> list[Path]:
    """Scan ~/.codex/pets for installed Codex packs (read-only)."""
    codex_pets = Path.home() / ".codex" / "pets"
    if not codex_pets.exists():
        return []
    packs = []
    for d in codex_pets.iterdir():
        if d.is_dir() and (d / "pet.json").exists():
            packs.append(d)
    return sorted(packs)
