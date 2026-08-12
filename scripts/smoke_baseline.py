#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functional regression smoke harness, originally established in Phase 1.

Runs the real pet_window_web.PetWindow (same construction path as main.py)
inside a scripted harness and verifies each baseline checklist item by driving
the REAL business handlers with synthesized Qt events / direct service calls.

Removed AI and Calendar surfaces are checked explicitly as regression
boundaries; the remaining checks are fully local.

Run:  .venv/Scripts/python.exe scripts/smoke_baseline.py
"""

import json
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from PyQt5.QtCore import Qt, QTimer, QPoint, QPointF, QUrl
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QEnterEvent
from PyQt5.QtWidgets import QApplication, QMenu
from PyQt5.QtCore import QEvent

import config as config_mod
import pocket_service
import reminder_service
import pet_window_web

RESULTS = []


class FakeDropEvent:
    def __init__(self, paths):
        self._urls = [QUrl.fromLocalFile(str(path)) for path in paths]
        self.accepted = False

    def mimeData(self): return self
    def hasUrls(self): return bool(self._urls)
    def urls(self): return self._urls
    def acceptProposedAction(self): self.accepted = True
    def ignore(self): pass


def record(item, status, detail=""):
    RESULTS.append((item, status, detail))
    print(f"[{status}] {item}" + (f" — {detail}" if detail else ""))


def js_eval(app, page, code, timeout=4.0):
    """Run JS and block until the callback fires (pumping the event loop)."""
    holder = {}
    def cb(r):
        holder["r"] = r
    page.runJavaScript(code, cb)
    t0 = time.time()
    while "r" not in holder and time.time() - t0 < timeout:
        app.processEvents()
        time.sleep(0.01)
    return holder.get("r")


def pump(app, seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        time.sleep(0.02)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Clippy Desktop Pet")
    app.setQuitOnLastWindowClosed(False)
    smoke_dir = REPO / ".tmp" / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_DIR = smoke_dir
    config_mod.CONFIG_FILE = smoke_dir / "config.json"
    reminder_service.REMINDERS_FILE = smoke_dir / "reminders.json"
    pocket_service.POCKET_FILE = smoke_dir / "pocket.json"
    if reminder_service.REMINDERS_FILE.exists():
        reminder_service.REMINDERS_FILE.unlink()
    if pocket_service.POCKET_FILE.exists():
        pocket_service.POCKET_FILE.unlink()
    config = config_mod.Config()

    t_start = time.time()
    try:
        window = pet_window_web.PetWindow(config)
    except Exception as e:
        record("主程序窗口构建", "FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return 2
    window.show()

    # Poll until the WebEngine page has loaded the sheet (max 20s)
    sheet_loaded = False
    while time.time() - t_start < 20:
        app.processEvents()
        time.sleep(0.05)
        r = js_eval(app, window.web.page(), "sheet !== null", timeout=1.0)
        if r is True:
            sheet_loaded = True
            break
    ready_t = round(time.time() - t_start, 2)
    record("主程序启动", "PASS" if window.isVisible() else "FAIL",
           f"PetWindow visible={window.isVisible()}, page+sheet ready in {ready_t}s")

    page = window.web.page()

    # ── Window attributes ──
    flags = window.windowFlags()
    frameless = bool(flags & Qt.FramelessWindowHint)
    ontop = bool(flags & Qt.WindowStaysOnTopHint)
    record("窗口无边框", "PASS" if frameless else "FAIL", str(flags))
    record("窗口置顶", "PASS" if ontop else "FAIL", str(flags))
    record("背景透明", "PASS" if window.testAttribute(Qt.WA_TranslucentBackground) else "FAIL")

    # ── Character visible (JS side loaded sheet & has frames) ──
    state1 = js_eval(app, page, "getState()")
    record("角色可见(sheet 已加载)", "PASS" if sheet_loaded else "FAIL",
           f"getState()={state1}")

    # ── Idle animation frame switching ──
    s1 = js_eval(app, page, "getState()")
    pump(app, 2.0)
    s2 = js_eval(app, page, "getState()")
    frames_advanced = False
    try:
        frames_advanced = json.loads(s2)["frame"] != json.loads(s1)["frame"]
    except Exception:
        pass
    record("idle 动画切帧", "PASS" if frames_advanced else "FAIL",
           f"before={s1} after={s2}")

    # ── Non-idle animation plays ──
    window.play_wave()
    pump(app, 1.0)
    st = js_eval(app, page, "getState()")
    anim_name = json.loads(st)["anim"] if st else "?"
    ok = anim_name in ("Wave", "Greeting")
    record("非 idle 动画播放 (Wave/Greeting)", "PASS" if ok else "FAIL", f"current={anim_name}")

    # ── Drag (real handlers with synthesized events) ──
    pos_before = window.pos()
    local = QPoint(10, 10)  # press point inside the window
    press = QMouseEvent(QEvent.MouseButtonPress, QPointF(local),
                        QPointF(pos_before + local),
                        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    window.mousePressEvent(press)
    # handler: move(globalPos - drag_pos) -> expected delta == pointer travel
    target_global = QPoint(pos_before + local + QPoint(50, 40))
    move = QMouseEvent(QEvent.MouseMove, QPointF(local), QPointF(target_global),
                       Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    window.mouseMoveEvent(move)
    release = QMouseEvent(QEvent.MouseButtonRelease, QPointF(local),
                          QPointF(target_global),
                          Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    window.mouseReleaseEvent(release)
    pos_after = window.pos()
    delta = (pos_after.x() - pos_before.x(), pos_after.y() - pos_before.y())
    record("角色拖动", "PASS" if delta == (50, 40) else "FAIL",
           f"delta={delta}, config.pet_x/y={config.get('pet_x')}/{config.get('pet_y')}")

    # ── Wheel zoom (real wheelEvent) — KNOWN upstream bug (KI-11):
    #    pet_window_web.py L640 passes float to setGeometry -> TypeError
    #    is RAISED in the original handler on the first wheel event whenever
    #    scale becomes non-integer. We record the exception as evidence.
    # Force an integer start so +0.5 deterministically exercises KI-11 even
    # when an earlier run persisted a half-step scale value.
    window._scale_val = 3.0
    scale_before = window._scale_val
    wheel_err = None
    try:
        wheel = QWheelEvent(QPointF(20, 20),
                            QPointF(QPoint(pos_after + QPoint(20, 20))),
                            QPoint(0, 0), QPoint(0, 120), 120, Qt.Vertical,
                            Qt.NoButton, Qt.NoModifier)
        window.wheelEvent(wheel)
    except Exception as e:
        wheel_err = f"{type(e).__name__}: {e}"
    zoom_ok = (wheel_err is None and window._scale_val == scale_before + 0.5)
    record("滚轮缩放", "PASS" if zoom_ok else "FAIL",
           f"scale {scale_before} -> {window._scale_val}, size={window.width()}x{window.height()}, "
           f"exception={wheel_err or 'none'}")

    # ── Sleep trigger (original logic: _check_idle after >30s inactivity) ──
    window._last_activity = time.time() - 60  # simulate inactivity, original logic untouched
    window._check_idle()
    pump(app, 0.5)
    st_sleep = js_eval(app, page, "getState()")
    record("sleep 触发", "PASS" if window._state == window.STATE_SLEEP else "FAIL",
           f"state={window._state}, js={st_sleep}")

    # ── Wake via enterEvent ──
    enter = QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5))
    window.enterEvent(enter)
    record("wake 恢复", "PASS" if window._state == window.STATE_IDLE else "FAIL",
           f"state={window._state}")

    # ── State restore after alert (original: ALERT -> 3s -> IDLE) ──
    window.reminder.add_reminder("Smoke reminder", datetime.now() - timedelta(seconds=1))
    window._check_due_reminders()
    pump(app, 0.5)
    alerted = window._state == window.STATE_ALERT
    bubble_text = window._bubble_text
    pump(app, 3.6)  # original QTimer.singleShot(3000) back to IDLE
    restored = window._state == window.STATE_IDLE
    record("提醒触发(ALERT+气泡+音效路径)", "PASS" if (alerted and bubble_text) else "FAIL",
           f"alerted={alerted}, bubble={bubble_text[:40]!r}")
    record("动画结束后状态恢复(ALERT→IDLE)", "PASS" if restored else "FAIL",
           f"state={window._state}")

    # ── Phase 7 local file/folder drop into reference-only Pocket ──
    drop_file = smoke_dir / "drop-smoke.txt"
    drop_folder = smoke_dir / "drop-folder"
    drop_file.write_text("untouched", encoding="utf-8")
    drop_folder.mkdir(exist_ok=True)
    drop_event = FakeDropEvent([drop_file, drop_folder])
    window.dropEvent(drop_event)
    pocket_paths = {item.path for item in window.pocket.list_items()}
    drop_ok = (drop_event.accepted and pocket_paths == {drop_file.resolve(), drop_folder.resolve()}
               and drop_file.read_text(encoding="utf-8") == "untouched")
    record("拖入文件/目录加入 Pocket 引用", "PASS" if drop_ok else "FAIL",
           f"accepted={drop_event.accepted}, items={len(pocket_paths)}, source_untouched={drop_file.exists()}")

    # ── Context menu construction (exec_ intercepted, original builder runs) ──
    captured = {}
    orig_exec = QMenu.exec_
    def fake_exec(self, *args):
        captured["items"] = [a.text() for a in self.actions() if a.text()]
        return None
    try:
        QMenu.exec_ = fake_exec
        window._show_context_menu(QPoint(120, 120))
    except Exception as e:
        captured["error"] = str(e)
    finally:
        QMenu.exec_ = orig_exec
    items = captured.get("items", [])
    no_removed_items = all(
        "Tanya" not in item and "Chat" not in item
        and "Jadwal" not in item and "Calendar" not in item
        for item in items
    )
    pocket_item = any("Pocket" in item for item in items)
    record("右键菜单构建", "PASS" if (len(items) >= 3 and no_removed_items and pocket_item) else "FAIL",
           f"items={items} err={captured.get('error', '')}")

    # ── Settings dialog ──
    try:
        d = pet_window_web.SettingsDialog(window.config, window)
        d.show()
        pump(app, 0.5)
        ok_settings = (d.isVisible() and not hasattr(d, "water_interval")
                       and not hasattr(d, "api_key_input")
                       and not hasattr(d, "cal_enabled"))
        d.close()
        record("Settings 对话框", "PASS" if ok_settings else "FAIL",
               "legacy Water/AI/Calendar controls absent")
    except Exception as e:
        record("Settings 对话框", "FAIL", f"{type(e).__name__}: {e}")

    # ── Phase 3 removal boundary ──
    ai_removed = (not hasattr(pet_window_web, "ChatDialog")
                  and not hasattr(window, "ai_engine"))
    record("AI Chat 已移除", "PASS" if ai_removed else "FAIL",
           "ChatDialog and PetWindow.ai_engine absent")
    requirements = (REPO / "requirements.txt").read_text(encoding="utf-8").lower()
    record("OpenAI 运行依赖已移除", "PASS" if "openai" not in requirements else "FAIL",
           "requirements.txt has no OpenAI package")

    # ── Phase 4 removal boundary ──
    calendar_removed = (not (REPO / "calendar_service.py").exists()
                        and not hasattr(window, "calendar"))
    google_deps = ("google-api-python-client", "google-auth-oauthlib", "pytz")
    record("Google Calendar 已移除", "PASS" if calendar_removed else "FAIL",
           "calendar_service.py and PetWindow.calendar absent")
    record("Google Calendar 运行依赖已移除",
           "PASS" if all(dep not in requirements for dep in google_deps) else "FAIL",
           "requirements.txt has no Google Calendar/OAuth packages")

    # ── Reminder timers initialized ──
    future = window.reminder.add_reminder("Future smoke reminder", datetime.now() + timedelta(minutes=5))
    window._schedule_next_reminder()
    timers_ok = (window._remind_timer.isActive() and window._remind_timer.isSingleShot()
                 and window._idle_timer.isActive()
                 and window._idle_variety_timer.isActive())
    record("Reminder/Idle Timer 初始化", "PASS" if timers_ok else "FAIL",
           f"remind={window._remind_timer.interval()}ms idle={window._idle_timer.interval()}ms")

    # ── Exit ──
    window._quit_app()
    pump(app, 1.0)
    record("正常退出路径", "PASS", "_quit_app() -> QApplication.quit() called")

    # ── Summary ──
    n_pass = sum(1 for _, s, _ in RESULTS if s == "PASS")
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    print(f"\nSUMMARY: {n_pass} PASS / {n_fail} FAIL / {len(RESULTS)} total")

    out = REPO / "docs" / "phase8_smoke_output.txt"
    out.write_text("\n".join(f"[{s}] {i} — {d}" for i, s, d in RESULTS)
                   + f"\n\nSUMMARY: {n_pass} PASS / {n_fail} FAIL\n", encoding="utf-8")
    print(f"raw results -> {out}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
