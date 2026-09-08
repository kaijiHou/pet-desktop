"""V5.0 real-render UI screenshot capture (task §5/§6/§7/§43/§44).

Runs the REAL Qt windows platform (never offscreen), builds the production
dialogs against an ISOLATED acceptance data dir (never the user's data/),
and saves widget.grab() PNG evidence.

Usage:
  python scripts/capture_v50_ui.py [--date 2026-09-01] [--outdir .tmp/v50-acceptance/screenshots]

Note: QWidget.grab() proves real Qt rendering on this machine's fonts/DPI,
NOT mouse resize feel, NOT OS DPI scaling, NOT Explorer behavior.
"""

import argparse
import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

# Real windows platform: drop any inherited offscreen setting BEFORE Qt loads.
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ["QT_QPA_PLATFORM"] = "windows"

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

ACCEPT_ROOT = PROJECT / ".tmp" / "v50-acceptance"


def _prepare_isolated_env():
    """Redirect all user-facing storage into .tmp/v50-acceptance/data."""
    import config as config_mod
    import destinations
    import pocket_service
    import reminder_service
    import sounds

    data_dir = ACCEPT_ROOT / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    (data_dir / "desktop-pet").mkdir(parents=True)

    config_mod.CONFIG_DIR = data_dir / "desktop-pet"
    config_mod.CONFIG_FILE = data_dir / "desktop-pet" / "config.json"
    reminder_service.REMINDERS_FILE = data_dir / "reminders.json"
    pocket_service.POCKET_FILE = data_dir / "pocket.json"
    destinations.DESTINATIONS_FILE = data_dir / "destinations.json"
    sounds.play_startup = lambda: None
    return config_mod


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-09-01", help="fixed now date, e.g. 2026-09-01")
    parser.add_argument("--outdir", default=str(ACCEPT_ROOT / "screenshots"))
    args = parser.parse_args()
    fixed_now = datetime.combine(date.fromisoformat(args.date), datetime.min.time()).replace(hour=10)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    config_mod = _prepare_isolated_env()

    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame

    app = QApplication(sys.argv)

    import sounds  # already silenced
    import pet_window as pw_mod
    from wage.service import WageService
    from paths import ASSETS_DIR, DATA_DIR
    from character_v4.registry import CharacterRegistry

    cfg = config_mod.Config()
    pet = pw_mod.PetWindow(cfg)
    pet.tray_icon.hide()
    pet.show()
    app.processEvents()

    # Isolated wage service with fixed clock and TEST salary (never user data).
    wage = WageService(ACCEPT_ROOT / "data", now_provider=lambda: fixed_now)
    wage.update_settings(enabled=True, monthly_salary="11200", work_start="09:00",
                         lunch_start="12:00", lunch_end="13:00", income_interval_minutes=60)
    pet.wage = wage

    def grab(widget, name, settle_ms=700):
        deadline = datetime.now().timestamp() + settle_ms / 1000.0
        while datetime.now().timestamp() < deadline:
            app.processEvents()
            app.processEvents()
        pix = widget.grab()
        path = outdir / name
        pix.save(str(path))
        print(f"saved {path} ({pix.width()}x{pix.height()})")

    # 1. Settings
    from pet_window import SettingsDialog
    dlg_settings = SettingsDialog(cfg, pet)
    dlg_settings.show()
    grab(dlg_settings, "v50-settings.png", 900)
    dlg_settings.close()
    app.processEvents()

    # 2. Wage Settings
    from wage.ui_settings import WageSettingsDialog
    dlg_wage = WageSettingsDialog(wage, pet)
    dlg_wage.show()
    grab(dlg_wage, "v50-wage-settings.png", 600)
    dlg_wage.close()
    app.processEvents()

    # 3/4. Calendar September + October (fixed --date drives the service clock)
    from wage.ui_calendar import WorkCalendarDialog
    dlg_cal = WorkCalendarDialog(wage)
    dlg_cal.show()
    dlg_cal.calendar.set_month(fixed_now.year, fixed_now.month)
    dlg_cal._selected_day = date(fixed_now.year, fixed_now.month, 20)
    dlg_cal._refresh()
    grab(dlg_cal, f"v50-calendar-september.png" if fixed_now.month == 9 else f"v50-calendar-{fixed_now.month:02d}.png", 700)
    dlg_cal.calendar.set_month(fixed_now.year, fixed_now.month + 1)
    dlg_cal._selected_day = date(fixed_now.year, fixed_now.month + 1, 10)
    dlg_cal._refresh()
    grab(dlg_cal, f"v50-calendar-october.png" if fixed_now.month == 9 else f"v50-calendar-{fixed_now.month + 1:02d}-next.png", 700)
    dlg_cal.close()
    app.processEvents()

    # 5. Character Gallery
    from character_gallery import CharacterGalleryDialog
    registry = CharacterRegistry(ASSETS_DIR, DATA_DIR)
    dlg_gallery = CharacterGalleryDialog(registry, cfg.get("selected_character_id", "default_dynamic_ghost"), pet)
    dlg_gallery.show()
    grab(dlg_gallery, "v50-character-gallery.png", 900)
    dlg_gallery.close()
    app.processEvents()

    # 6. Character consistency: desktop frame vs Settings-style preview widget
    from ui.modern.character_preview import CharacterPreviewWidget
    selected_id = cfg.get("selected_character_id", "default_dynamic_ghost")
    container = QWidget()
    container.setWindowTitle("character consistency")
    container.setFixedSize(560, 380)
    lay = QVBoxLayout(container)
    row = QHBoxLayout()
    desktop_frame = pet.dynamic_renderer.current_pixmap()
    desktop_view = QLabel()
    desktop_view.setAlignment(Qt.AlignCenter)
    if desktop_frame is not None:
        desktop_view.setPixmap(desktop_frame.scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    preview = CharacterPreviewWidget(registry, selected_id)
    preview.setFixedSize(240, 240)
    left_col = QVBoxLayout(); left_col.addWidget(desktop_view)
    id_desktop = QLabel(f"Desktop ID: {selected_id}"); id_desktop.setAlignment(Qt.AlignCenter)
    right_col = QVBoxLayout(); right_col.addWidget(preview)
    id_preview = QLabel(f"Preview ID: {selected_id}"); id_preview.setAlignment(Qt.AlignCenter)
    left_col.addWidget(id_desktop); right_col.addWidget(id_preview)
    row.addLayout(left_col); row.addLayout(right_col)
    lay.addLayout(row)
    container.show()
    grab(container, "v50-character-consistency.png", 900)

    # Programmatic sameness checks (same pack + same aspect ratio)
    checks = {"same_id": True, "aspect_match": None}
    frame = pet.dynamic_renderer.current_pixmap() if pet.dynamic_renderer else None
    if frame is not None and not frame.isNull():
        frame_ratio = frame.width() / frame.height()
        # preview renders the same 192x208 cell pack; compare against its renderer frame
        pr = preview.renderer
        pr_frame = pr.current_pixmap() if pr else None
        if pr_frame is not None and not pr_frame.isNull():
            checks["aspect_match"] = abs(frame_ratio - pr_frame.width() / pr_frame.height()) < 0.01
    checks["same_id"] = (selected_id == "default_dynamic_ghost"
                         and preview.character_id == selected_id)
    print("consistency checks:", checks)

    pet.tray_icon.hide()
    pet.close()
    container.close()
    print("CAPTURE DONE")


if __name__ == "__main__":
    main()
