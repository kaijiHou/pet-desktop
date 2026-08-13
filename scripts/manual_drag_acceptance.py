#!/usr/bin/env python
"""Show one isolated Pocket item beside a uniquely named Explorer target."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pocket_service
from pocket_ui import PocketDialog


SESSION_FILE = ROOT / ".tmp" / "tests" / "phase17_drag_session.json"
RESULT_FILE = ROOT / ".tmp" / "tests" / "phase17_drag_result.json"


def main():
    test_root = ROOT / ".tmp" / "tests"
    test_root.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="phase17-drag-", dir=test_root))
    source = run_root / "drag-source.txt"
    target = run_root / "drag-target"
    store = run_root / "pocket.json"
    source.write_text("phase17-real-explorer-drag", encoding="utf-8")
    target.mkdir()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    service = pocket_service.PocketService(store)
    service.add(source)
    dialog = PocketDialog(service)
    dialog.setWindowTitle("Phase 17 Pocket Drag Acceptance")
    dialog.setWindowFlag(Qt.Window, True)
    dialog.setGeometry(40, 100, 760, 430)
    dialog.finished.connect(app.quit)
    dialog.show()

    session = {"source": str(source), "target": str(target), "expected": str(target / source.name)}
    SESSION_FILE.write_text(
        json.dumps(session, indent=2),
        encoding="utf-8",
    )
    subprocess.Popen(["explorer.exe", str(target)])
    app.exec_()

    copied = target / source.name
    result = {
        **session,
        "status": "PASS" if copied.exists() and source.exists() else "FAIL",
        "target_copy_exists": copied.exists(),
        "source_still_exists": source.exists(),
    }
    RESULT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
