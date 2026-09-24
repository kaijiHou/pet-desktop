"""Contract tests for the stdlib-only release artifact helper."""

from argparse import Namespace
import json
from pathlib import Path
import zipfile

import pytest

from scripts import release_artifacts


@pytest.mark.unit
def test_release_package_manifest_hash_and_extraction(test_temp_root, capsys):
    package_dir = test_temp_root / "DesktopPet"
    assets = package_dir / "assets"
    assets.mkdir(parents=True)
    (package_dir / "DesktopPet.exe").write_bytes(b"isolated executable fixture")
    (assets / "README.md").write_text("asset note", encoding="utf-8")
    release_dir = test_temp_root / "release"
    zip_path = release_dir / "DesktopPet-windows-x64.zip"
    args = Namespace(
        package_dir=str(package_dir), release_dir=str(release_dir), zip_path=str(zip_path),
        version="V5.2", git_sha="a" * 40, build_time="2026-09-24T12:00:00+08:00",
    )

    release_artifacts.package(args)
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "V5.2"
    assert manifest["git_sha"] == "a" * 40
    assert manifest["zip_sha256"] == release_artifacts.sha256(zip_path)
    release_artifacts.verify(Namespace(
        manifest=str(release_dir / "manifest.json"), zip_path=str(zip_path), version="V5.2",
    ))
    log_path = test_temp_root / "app.log"
    log_path.write_text(f"app_version=V5.2 git_sha={'a' * 40}\n", encoding="utf-8")
    release_artifacts.verify_log(Namespace(manifest=str(release_dir / "manifest.json"), log=str(log_path)))
    assert "ArtifactZIP_SHA256=" in capsys.readouterr().out

    extracted = test_temp_root / "extracted"
    release_artifacts.extract(Namespace(zip_path=str(zip_path), destination=str(extracted)))
    assert (extracted / "DesktopPet" / "DesktopPet.exe").read_bytes() == b"isolated executable fixture"
    assert (extracted / "DesktopPet" / "assets" / "README.md").read_text(encoding="utf-8") == "asset note"


@pytest.mark.unit
def test_release_extractor_rejects_zip_path_traversal(test_temp_root):
    archive_path = test_temp_root / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escaped.txt", "no")
    destination = test_temp_root / "extracted"

    with pytest.raises(ValueError, match="Unsafe ZIP entry"):
        release_artifacts.extract(Namespace(zip_path=str(archive_path), destination=str(destination)))
    assert not (test_temp_root / "escaped.txt").exists()
