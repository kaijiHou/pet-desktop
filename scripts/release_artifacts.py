"""Build and inspect release artifacts using only Python's standard library."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_build_info(args):
    write_json(args.path, {
        "version": args.version,
        "git_sha": args.git_sha,
        "build_time": args.build_time,
    })


def package(args):
    package_dir = Path(args.package_dir).resolve()
    zip_path = Path(args.zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(package_dir.name, *path.relative_to(package_dir).parts).as_posix())

    artifact_hash = sha256(zip_path)
    write_json(Path(args.release_dir) / "manifest.json", {
        "name": "DesktopPet",
        "format": "windows-x64-one-folder",
        "entrypoint": "DesktopPet\\DesktopPet.exe",
        "zip": zip_path.name,
        "version": args.version,
        "git_sha": args.git_sha,
        "zip_sha256": artifact_hash,
        "sha256": artifact_hash,
        "build_time": args.build_time,
        "built_at": args.build_time,
    })
    print(f"ZIP_SHA256={artifact_hash}")


def extract(args):
    destination = Path(args.destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip_path) as archive:
        for info in archive.infolist():
            relative = PurePosixPath(info.filename.replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe ZIP entry: {info.filename}")
            target = destination.joinpath(*relative.parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def verify(args):
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    actual_hash = sha256(args.zip_path)
    if manifest.get("version") != args.version:
        raise ValueError(f"Expected {args.version}, found {manifest.get('version')}")
    if manifest.get("zip_sha256") != actual_hash or manifest.get("sha256") != actual_hash:
        raise ValueError("ZIP SHA256 does not match release/manifest.json")
    print(f"ManifestVersion={manifest['version']}")
    print(f"ReleaseGitSHA={manifest['git_sha']}")
    print(f"ArtifactZIP_SHA256={actual_hash}")


def verify_log(args):
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    log_text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    expected = (f"app_version={manifest['version']}", f"git_sha={manifest['git_sha']}")
    missing = [value for value in expected if value not in log_text]
    if missing:
        raise ValueError(f"Build identity missing from app log: {', '.join(missing)}")
    print(f"BuildIdentityLog=PASS git_sha={manifest['git_sha']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build_info = commands.add_parser("write-build-info")
    build_info.add_argument("path")
    build_info.add_argument("--version", required=True)
    build_info.add_argument("--git-sha", required=True)
    build_info.add_argument("--build-time", required=True)
    build_info.set_defaults(run=write_build_info)

    pack = commands.add_parser("package")
    pack.add_argument("--package-dir", required=True)
    pack.add_argument("--release-dir", required=True)
    pack.add_argument("--zip-path", required=True)
    pack.add_argument("--version", required=True)
    pack.add_argument("--git-sha", required=True)
    pack.add_argument("--build-time", required=True)
    pack.set_defaults(run=package)

    unpack = commands.add_parser("extract")
    unpack.add_argument("--zip-path", required=True)
    unpack.add_argument("--destination", required=True)
    unpack.set_defaults(run=extract)

    check = commands.add_parser("verify")
    check.add_argument("--manifest", required=True)
    check.add_argument("--zip-path", required=True)
    check.add_argument("--version", required=True)
    check.set_defaults(run=verify)

    log_check = commands.add_parser("verify-log")
    log_check.add_argument("--manifest", required=True)
    log_check.add_argument("--log", required=True)
    log_check.set_defaults(run=verify_log)

    digest = commands.add_parser("sha256")
    digest.add_argument("path")
    digest.set_defaults(run=lambda args: print(sha256(args.path)))

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
