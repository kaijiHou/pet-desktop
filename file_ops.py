"""Explicit, non-overwriting copy and move operations."""

from dataclasses import dataclass
from pathlib import Path
import shutil


@dataclass(frozen=True)
class OperationItemResult:
    source: Path
    destination: Path | None
    status: str
    error: str = ""


@dataclass(frozen=True)
class OperationReport:
    action: str
    items: list[OperationItemResult]

    @property
    def succeeded(self):
        return sum(item.status == "succeeded" for item in self.items)

    @property
    def skipped(self):
        return sum(item.status == "skipped" for item in self.items)

    @property
    def failed(self):
        return sum(item.status == "failed" for item in self.items)


class FileOperationService:
    """Copy or move selected paths with explicit conflict behavior."""

    def copy(self, sources, destination, conflict="rename") -> OperationReport:
        return self._run("copy", sources, destination, conflict)

    def move(self, sources, destination, conflict="rename") -> OperationReport:
        return self._run("move", sources, destination, conflict)

    def _run(self, action, sources, destination, conflict):
        if conflict not in {"rename", "skip"}:
            raise ValueError("conflict must be 'rename' or 'skip'")
        destination = Path(destination).expanduser().resolve()
        results = []
        for raw_source in sources:
            source = Path(raw_source).expanduser().resolve()
            if not source.exists():
                results.append(OperationItemResult(source, None, "failed", "Source not found"))
                continue
            if not destination.is_dir():
                results.append(OperationItemResult(source, None, "failed", "Destination is not a directory"))
                continue
            if source.is_dir() and destination.is_relative_to(source):
                results.append(OperationItemResult(
                    source, None, "failed", "Destination cannot be inside the source directory"
                ))
                continue

            target = destination / source.name
            if target.exists():
                if conflict == "skip":
                    results.append(OperationItemResult(source, target, "skipped", "Destination exists"))
                    continue
                target = self._unique_target(target)
            try:
                if action == "copy":
                    if source.is_dir():
                        shutil.copytree(source, target)
                    else:
                        shutil.copy2(source, target)
                else:
                    shutil.move(str(source), str(target))
                results.append(OperationItemResult(source, target, "succeeded"))
            except OSError as exc:
                results.append(OperationItemResult(source, target, "failed", str(exc)))
        return OperationReport(action, results)

    @staticmethod
    def _unique_target(target: Path) -> Path:
        stem = target.stem if target.suffix else target.name
        suffix = target.suffix
        index = 1
        while True:
            candidate = target.with_name(f"{stem} ({index}){suffix}")
            if not candidate.exists():
                return candidate
            index += 1
