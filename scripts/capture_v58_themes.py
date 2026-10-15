"""Capture V5.8 themed QuickPanel / WorkCalendar renders in a sandbox.

Every user data surface is redirected to a temp sandbox (config, reminders,
pocket, destinations, wage, ui_skins) — the running pet's real data is never
touched. Dev-time helper only; not part of the delivery chain.

Usage:
  python scripts/capture_v58_themes.py --skins sakura --panels qp cal \
      --out docs/screenshots/v58 --prefix before --scale 1.0
"""

import argparse
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--skins", default="sakura")
parser.add_argument("--panels", default="qp,cal")
parser.add_argument("--picker", action="store_true", help="capture the theme picker (cute+cool tabs)")
parser.add_argument("--out", default="docs/screenshots/v58")
parser.add_argument("--prefix", default="v58")
parser.add_argument("--scale", default="1.0")
args = parser.parse_args()

SANDBOX = PROJECT_ROOT / ".tmp" / f"v58-capture-{uuid4().hex[:8]}"
os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["QT_SCALE_FACTOR"] = args.scale
os.environ["TEMP"] = str(SANDBOX)
os.environ["TMP"] = str(SANDBOX)
sys.path.insert(0, str(PROJECT_ROOT))

# ── sandbox ALL five user data surfaces before importing app modules ──
import config as config_mod

config_mod.CONFIG_DIR = SANDBOX / "config"
config_mod.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
config_mod.CONFIG_FILE = config_mod.CONFIG_DIR / "config.json"

import reminder_service  # noqa: E402

reminder_service.REMINDERS_FILE = SANDBOX / "reminders.json"

import pocket_service  # noqa: E402

pocket_service.POCKET_FILE = SANDBOX / "pocket.json"

import destinations  # noqa: E402

destinations.DESTINATIONS_FILE = SANDBOX / "destinations.json"

import ui_skin  # noqa: E402

ui_skin.SKINS_FILE = SANDBOX / "ui_skins.json"

from wage.service import WageService  # noqa: E402

WAGE_DIR = SANDBOX / "wage"
WAGE_DIR.mkdir(parents=True, exist_ok=True)
(WAGE_DIR / "wage_settings.json").write_text(
    '{"enabled": true, "monthly_salary": "14000", "work_start": "08:30",'
    ' "work_end": "17:00", "lunch_start": "11:30", "lunch_end": "13:00"}',
    encoding="utf-8",
)

NOW = datetime(2026, 10, 14, 15, 0, 0)


def main():
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication

    from destinations import DestinationService

    app = QApplication.instance() or QApplication([sys.argv[0]])

    service = WageService(WAGE_DIR, now_provider=lambda: NOW)
    service.edit_clock_out(date(2026, 10, 9), datetime(2026, 10, 9, 19, 0))
    service.edit_clock_out(date(2026, 10, 13), datetime(2026, 10, 13, 20, 10))

    demo_dir = SANDBOX / "folders"
    demo_dir.mkdir(exist_ok=True)
    for name in ("工作", "资料"):
        (demo_dir / name).mkdir(exist_ok=True)
    dest = DestinationService(SANDBOX / "destinations.json")
    dest.add_favorite(demo_dir / "工作")
    dest.add_favorite(demo_dir / "资料")

    class FakeItem:
        def __init__(self, name):
            self.name, self.exists = name, True

    class FakeReminder:
        def __init__(self, when, content):
            self.due_at, self.content = when, content

    class DemoPet:
        wage = service
        destination_service = dest

        class pocket:
            list_items = staticmethod(
                lambda: [FakeItem("需求文档 v3.docx"), FakeItem("报表-10月.xlsx")])

        class reminder:
            list_reminders = staticmethod(lambda: [
                FakeReminder(datetime(2026, 10, 29, 9, 0), "续费 Codex 会员"),
                FakeReminder(datetime(2026, 10, 20, 14, 0), "周会前更新排期"),
            ])

    out_dir = PROJECT_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    import theme

    skins = [s.strip() for s in args.skins.split(",") if s.strip()]
    panels = [p.strip() for p in args.panels.split(",") if p.strip()]
    for skin_id in skins:
        ui_skin._active_id = skin_id          # demo only — never persist
        ui_skin.initialize()
        theme.apply(app)
        if "qp" in panels:
            from quick_panel import QuickPanel
            panel = QuickPanel(DemoPet(), destinations=dest)
            panel.setAttribute(Qt.WA_DontShowOnScreen, True)
            panel.ensurePolished()
            panel.adjustSize()
            if panel.layout():
                panel.layout().activate()
            deadline = time.monotonic() + 0.25
            while time.monotonic() < deadline:
                app.processEvents()
            image = _render(panel)
            target = out_dir / f"{args.prefix}-quickpanel-{skin_id}.png"
            _save(image, target)
            panel.close()
            app.processEvents()
        if "cal" in panels:
            from wage.ui_calendar import WorkCalendarDialog
            dialog = WorkCalendarDialog(service, None)
            dialog.setAttribute(Qt.WA_DontShowOnScreen, True)
            hint = dialog.sizeHint().height()
            dialog.resize(980, max(720, hint))
            dialog.ensurePolished()
            dialog.layout().activate()
            if dialog.layout():
                dialog.layout().activate()
            app.processEvents()
            deadline = time.monotonic() + 0.25
            while time.monotonic() < deadline:
                app.processEvents()
            image = _render(dialog)
            target = out_dir / f"{args.prefix}-calendar-{skin_id}.png"
            _save(image, target)
            dialog.close()
            app.processEvents()
        if args.picker:
            from ui_theme_picker import ThemePickerDialog
            picker = ThemePickerDialog()
            picker.setAttribute(Qt.WA_DontShowOnScreen, True)
            picker.ensurePolished()
            picker.layout().activate()
            app.processEvents()
            image = _render(picker)
            _save(image, out_dir / f"{args.prefix}-theme-picker-{skin_id}.png")
            picker.close()
            app.processEvents()
    print("captures done ->", out_dir)


def _render(widget):
    # grab() honours QT_SCALE_FACTOR (physical pixels), so DPI runs are real;
    # plain render() would stay at logical size and prove nothing for DPI.
    image = widget.grab()
    return image


def _save(image, target: Path):
    if image.isNull() or image.width() < 200 or image.height() < 100:
        raise RuntimeError(f"undersized capture for {target.name}: {image.size()}")
    if not image.save(str(target), "PNG"):
        raise RuntimeError(f"could not save {target}")
    print(f"{target.name}: {image.width()}x{image.height()} {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
