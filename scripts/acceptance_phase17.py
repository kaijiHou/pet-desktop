#!/usr/bin/env python
"""Phase 17 real-platform acceptance checks, isolated to the project temp tree."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.pop("QT_QPA_PLATFORM", None)

from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

import config as config_mod
import destinations as destinations_mod
import pocket_service as pocket_mod
import reminder_service as reminder_mod
import sounds
from config import Config
from file_ops import FileOperationService
from file_watch import FileWatchService
from pet_sprite import PetSpriteLoader
from pet_window import PetWindow


RESULT_PATH = ROOT / "docs" / "phase17_acceptance.json"
PREVIEW_PATH = ROOT / "docs" / "phase17_native_preview.png"


def wait_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


def record(results, name, passed, detail=""):
    results.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def prepare_runtime(run_root):
    config_mod.CONFIG_DIR = run_root / "state"
    config_mod.CONFIG_FILE = config_mod.CONFIG_DIR / "config.json"
    reminder_mod.REMINDERS_FILE = run_root / "state" / "reminders.json"
    pocket_mod.POCKET_FILE = run_root / "state" / "pocket.json"
    destinations_mod.DESTINATIONS_FILE = run_root / "state" / "destinations.json"
    sounds.play_startup = lambda: None


def main():
    temp_parent = ROOT / ".tmp" / "tests"
    temp_parent.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="phase17-", dir=temp_parent))
    results = []
    watcher = None
    window = None
    saved_sound = sounds.play_startup

    prepare_runtime(run_root)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    try:
        config = Config()
        window = PetWindow(config)
        window.tray_icon.hide()

        # Render the repository-owned neutral placeholder, independent of any
        # ignored local sprite sheet used during development.
        placeholder_assets = run_root / "placeholder-assets"
        placeholder_assets.mkdir()
        shutil.copy2(ROOT / "assets" / "animations.json", placeholder_assets / "animations.json")
        window.sprite_loader = PetSpriteLoader(placeholder_assets, config.get("pet_scale", 3))
        window.show()
        QTest.qWait(200)
        grab = window.grab()
        saved = grab.save(str(PREVIEW_PATH), "PNG")
        has_visible_pixels = not grab.toImage().isNull() and grab.toImage().hasAlphaChannel()
        record(results, "原生透明窗口可见绘制", saved and has_visible_pixels,
               f"{window.width()}x{window.height()}")

        start_pos = window.pos()
        press = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPointF(20, 20),
            QPointF(start_pos + QPoint(20, 20)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
        )
        move = QMouseEvent(
            QMouseEvent.MouseMove, QPointF(44, 38),
            QPointF(start_pos + QPoint(44, 38)), Qt.NoButton, Qt.LeftButton, Qt.NoModifier,
        )
        release = QMouseEvent(
            QMouseEvent.MouseButtonRelease, QPointF(44, 38),
            QPointF(start_pos + QPoint(44, 38)), Qt.LeftButton, Qt.NoButton, Qt.NoModifier,
        )
        window.mousePressEvent(press)
        window.mouseMoveEvent(move)
        window.mouseReleaseEvent(release)
        record(results, "角色拖动", window.pos() != start_pos,
               f"{start_pos.x()},{start_pos.y()} -> {window.x()},{window.y()}")

        old_size = window.size()
        window._change_scale(0.5)
        record(results, "整数安全缩放", window.size() != old_size and isinstance(window.width(), int),
               f"{old_size.width()}x{old_size.height()} -> {window.width()}x{window.height()}")

        reminder = window.reminder.add_reminder("Phase 17 due", reminder_mod.datetime.now())
        window._check_due_reminders()
        record(results, "本地提醒到期", reminder.status == "completed" and "Phase 17 due" in window._bubble_text)

        source = run_root / "source.txt"
        source.write_text("phase17", encoding="utf-8")
        item = window.pocket.add(source)
        record(results, "Pocket仅保存引用", item.path == source.resolve() and source.read_text(encoding="utf-8") == "phase17")

        copy_dir = run_root / "copy-target"
        move_dir = run_root / "move-target"
        copy_dir.mkdir()
        move_dir.mkdir()
        operations = FileOperationService()
        copy_report = operations.copy([source], copy_dir)
        copied = copy_dir / source.name
        copy_ok = copy_report.succeeded == 1 and source.exists() and copied.exists()
        move_report = operations.move([copied], move_dir)
        moved = move_dir / source.name
        record(results, "真实本地复制", copy_ok)
        record(results, "真实本地移动", move_report.succeeded == 1 and not copied.exists() and moved.exists())

        watched = run_root / "watched"
        watched.mkdir()
        events = []
        watcher = FileWatchService()
        watcher.on_change = events.append
        watcher.watch(watched)
        QTest.qWait(150)
        first = watched / "first.txt"
        second = watched / "second.txt"
        first.write_text("one", encoding="utf-8")
        first.write_text("two", encoding="utf-8")
        first.rename(second)
        second.unlink()
        expected = {"added", "modified", "renamed_from", "renamed_to", "removed"}
        complete = wait_until(lambda: expected.issubset({event.action for event in events}))
        actions = sorted({event.action for event in events})
        record(results, "ReadDirectoryChangesW真实事件", complete, ", ".join(actions))

        record(results, "WebEngine运行时不存在", "PyQtWebEngine" not in sys.modules)
    finally:
        if watcher:
            watcher.stop_all()
        if window:
            window.file_watch.stop_all()
            window.tray_icon.hide()
            window.close()
        sounds.play_startup = saved_sound
        QApplication.processEvents()

    failures = [result for result in results if result["status"] != "PASS"]
    payload = {
        "platform": sys.platform,
        "qt_platform": QApplication.platformName(),
        "temp_root": str(run_root),
        "summary": {"passed": len(results) - len(failures), "failed": len(failures)},
        "results": results,
    }
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSUMMARY: {payload['summary']['passed']} PASS / {payload['summary']['failed']} FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
