#!/usr/bin/env python
"""Phase 16 native-renderer functional smoke harness."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import QPoint, QPointF, Qt, QUrl
from PyQt5.QtGui import QEnterEvent, QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QApplication, QMenu

import config as config_mod
import destinations
import pocket_service
import reminder_service
import pet_window


RESULTS = []


def record(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((name, status, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


class DropEvent:
    def __init__(self, paths):
        self._urls = [QUrl.fromLocalFile(str(path)) for path in paths]
        self.accepted = False
    def mimeData(self): return self
    def hasUrls(self): return bool(self._urls)
    def urls(self): return self._urls
    def acceptProposedAction(self): self.accepted = True
    def ignore(self): pass


def main():
    smoke = ROOT / ".tmp" / "native-smoke"
    smoke.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_DIR = smoke
    config_mod.CONFIG_FILE = smoke / "config.json"
    reminder_service.REMINDERS_FILE = smoke / "reminders.json"
    pocket_service.POCKET_FILE = smoke / "pocket.json"
    destinations.DESTINATIONS_FILE = smoke / "destinations.json"
    for path in (reminder_service.REMINDERS_FILE, pocket_service.POCKET_FILE):
        if path.exists(): path.unlink()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = pet_window.PetWindow(config_mod.Config())
    window.tray_icon.hide()
    window.show()
    pump(app, 0.3)

    flags = window.windowFlags()
    record("原生主窗口启动", window.isVisible() and not hasattr(window, "web"))
    record("窗口无边框", bool(flags & Qt.FramelessWindowHint))
    record("窗口置顶", bool(flags & Qt.WindowStaysOnTopHint))
    record("原生帧可绘制", not window.sprite_loader.get_frame("RestPose", 0).getbbox() is None,
           f"placeholder={window.sprite_loader._sprites.using_placeholder}")

    window.play_animation("Wave")
    pump(app, 0.25)
    record("43组动画原生播放", window._animation == "Wave" and window._frame > 0,
           f"animation={window._animation}, frame={window._frame}")

    start = window.pos()
    press = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(20, 20),
                        QPointF(start + QPoint(20, 20)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    window.mousePressEvent(press)
    move = QMouseEvent(QMouseEvent.MouseMove, QPointF(70, 60),
                       QPointF(start + QPoint(70, 60)), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
    window.mouseMoveEvent(move)
    record("角色拖动", window.pos() - start == QPoint(50, 40))

    scale = float(window.config.get("pet_scale"))
    wheel = QWheelEvent(QPointF(20, 20), QPointF(window.pos() + QPoint(20, 20)),
                        QPoint(), QPoint(0, 120), 120, Qt.Vertical, Qt.NoButton, Qt.NoModifier)
    window.wheelEvent(wheel)
    record("滚轮缩放(KI-11已修复)", window.config.get("pet_scale") == round(scale + 0.1, 1))

    window._last_activity = time.time() - 400
    window._check_idle()
    record("sleep触发", window._state == window.STATE_SLEEP)
    window.enterEvent(QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1)))
    record("wake恢复", window._state == window.STATE_IDLE)

    window.reminder.add_reminder("Native smoke", datetime.now() - timedelta(seconds=1))
    window._check_due_reminders()
    record("本地提醒触发", "Native smoke" in window._bubble_text)

    source = smoke / "drop.txt"; source.write_text("untouched", encoding="utf-8")
    folder = smoke / "drop-folder"; folder.mkdir(exist_ok=True)
    drop = DropEvent([source, folder])
    window.dropEvent(drop)
    record("拖入Pocket引用", drop.accepted and len(window.pocket.list_items()) == 2
           and source.read_text(encoding="utf-8") == "untouched")

    captured = []
    original_exec = QMenu.exec_
    QMenu.exec_ = lambda menu, *args: (captured.extend(a.text() for a in menu.actions() if a.text()), None)[1]
    try: window._show_context_menu(QPoint(10, 10))
    finally: QMenu.exec_ = original_exec
    record("右键菜单构建", any("Pocket" in item for item in captured)
           and any("Reminder" in item for item in captured), str(captured))

    record("单次Reminder定时器", window._remind_timer.isSingleShot())
    record("idle静帧优化", window._idle_variety_timer.isSingleShot())
    record("无WebEngine子系统", "PyQtWebEngine" not in (ROOT / "requirements.txt").read_text())

    window._quit_app()
    pump(app, 0.1)
    passed = sum(status == "PASS" for _, status, _ in RESULTS)
    failed = len(RESULTS) - passed
    print(f"\nSUMMARY: {passed} PASS / {failed} FAIL / {len(RESULTS)} total")
    output = ROOT / "docs" / "phase16_smoke_output.txt"
    output.write_text("\n".join(f"[{status}] {name} — {detail}".rstrip(" —")
                                for name, status, detail in RESULTS), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
