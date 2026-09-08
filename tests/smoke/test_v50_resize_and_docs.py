"""V5.0 resize/layout contracts and the release-docs contract (task §14/§15/§37)."""

import sys

import pytest
from PyQt5.QtCore import QPoint, QRect, Qt


# ── §15 detect_resize_edge pure function ─────────────────────────────────

def test_detect_resize_edge_all_eight_directions():
    from ui.modern.dialog import detect_resize_edge

    rect = QRect(0, 0, 400, 300)
    m = 7
    assert detect_resize_edge(QPoint(3, 150), rect, m) & Qt.LeftEdge
    assert detect_resize_edge(QPoint(397, 150), rect, m) & Qt.RightEdge
    assert detect_resize_edge(QPoint(200, 2), rect, m) & Qt.TopEdge
    assert detect_resize_edge(QPoint(200, 297), rect, m) & Qt.BottomEdge
    assert detect_resize_edge(QPoint(2, 2), rect, m) == (Qt.LeftEdge | Qt.TopEdge)
    assert detect_resize_edge(QPoint(398, 2), rect, m) == (Qt.RightEdge | Qt.TopEdge)
    assert detect_resize_edge(QPoint(2, 298), rect, m) == (Qt.LeftEdge | Qt.BottomEdge)
    assert detect_resize_edge(QPoint(398, 298), rect, m) == (Qt.RightEdge | Qt.BottomEdge)
    # center hits nothing
    assert detect_resize_edge(QPoint(200, 150), rect, m) == Qt.Edges()
    # disabled/invalid inputs
    assert detect_resize_edge(QPoint(2, 2), rect, 0) == Qt.Edges()


# ── §14 calendar programmatic resize contract ────────────────────────────

def _make_calendar(qapp, test_temp_root):
    import shutil
    from datetime import datetime
    from wage.service import WageService
    from wage.ui_calendar import WorkCalendarDialog
    from tests.conftest import TEST_TEMP_ROOT

    tmp = TEST_TEMP_ROOT / "gui" / "v50_calendar_resize"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    svc = WageService(tmp, now_provider=lambda: datetime(2026, 9, 20, 10, 0))
    svc.update_settings(enabled=True, monthly_salary="11200", manual_workday_count=None)
    dlg = WorkCalendarDialog(svc)
    return dlg


def test_work_calendar_programmatic_resize_large(qapp, test_temp_root):
    dlg = _make_calendar(qapp, test_temp_root)
    try:
        dlg.show()
        dlg.resize(1200, 800)
        qapp.processEvents()
        assert dlg.calendar.isVisible() and dlg.calendar.width() > 500
        assert dlg.detail_card.isVisible() and dlg.detail_card.width() > 200
        for card in dlg.stat_cards.values():
            assert card.isVisible(), "stat cards must survive large resize"
        assert dlg.width() == 1200 and dlg.height() == 800
    finally:
        dlg.close()


def test_work_calendar_minimum_size_keeps_detail(qapp, test_temp_root):
    dlg = _make_calendar(qapp, test_temp_root)
    try:
        dlg.show()
        min_size = dlg.minimumSize()
        dlg.resize(min_size)
        qapp.processEvents()
        for child in dlg.findChildren(object):
            pass
        assert dlg.calendar.isVisible()
        assert dlg.detail_card.isVisible(), "detail panel must not vanish at minimum size"
        for card in dlg.stat_cards.values():
            assert card.isVisible()
            assert card.width() > 0 and card.height() > 0, "no negative/zero card geometry"
    finally:
        dlg.close()


# ── §24 timer leak upgrades ───────────────────────────────────────────────

def test_settings_open_close_20x_no_timer_growth(pet_window):
    from pet_window import SettingsDialog
    from PyQt5.QtWidgets import QApplication

    def active_timer_count():
        return sum(1 for w in QApplication.allWidgets()
                   for t in w.findChildren(type(pet_window._sem_timer)) if t.isActive())

    baseline = active_timer_count()
    for _ in range(20):
        dlg = SettingsDialog(pet_window.config, pet_window)
        dlg.show()
        QApplication.processEvents()
        dlg.close()
        QApplication.processEvents()
    assert active_timer_count() <= baseline + 1, "Settings open/close leaked timers"


def test_gallery_switch_20x_preview_timers_bounded(pet_window_dynamic):
    from character_gallery import CharacterGalleryDialog
    from PyQt5.QtWidgets import QApplication
    from paths import ASSETS_DIR, DATA_DIR
    from character_v4.registry import CharacterRegistry

    registry = CharacterRegistry(ASSETS_DIR, DATA_DIR)
    current = pet_window_dynamic.config.get("selected_character_id", "default_dynamic_ghost")

    def active_timer_count():
        return sum(1 for w in QApplication.allWidgets()
                   for t in w.findChildren(type(pet_window_dynamic._sem_timer)) if t.isActive())

    baseline = active_timer_count()
    for i in range(20):
        dlg = CharacterGalleryDialog(registry, current, pet_window_dynamic)
        dlg.show()
        QApplication.processEvents()
        dlg.close()
        QApplication.processEvents()
    assert active_timer_count() <= baseline + 1, "gallery preview switching leaked timers"


# ── §37 release docs contract ─────────────────────────────────────────────

def test_v50_release_docs_exist():
    from pathlib import Path
    docs = Path(__file__).resolve().parents[2] / "docs"
    assert (docs / "V50_CHANGE_SUMMARY.md").exists(), "version change summary is mandatory"
    assert (docs / "CHANGE_SUMMARY_TEMPLATE.md").exists(), "template must stay in repo"
    assert (docs / "V50_REAL_ACCEPTANCE.md").exists()
