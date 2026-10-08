"""V5.4 money popup contract: no Python paintEvent, input-transparent, pops."""

import pytest


def test_money_popup_no_python_paintevent():
    """IME-crash hardening: the chip must be C++-painted (pure QLabel)."""
    from money_popup import MoneyPopup
    assert "paintEvent" not in vars(MoneyPopup),         "custom Python paintEvent is the IME crash carrier — keep it out"


def test_money_popup_pops_above_anchor(qapp):
    from money_popup import MoneyPopup
    from PyQt5.QtCore import QRect

    popup = MoneyPopup()
    anchor = QRect(600, 400, 300, 300)
    popup.pop("¥238.46", anchor)
    try:
        assert popup.isVisible()
        assert popup.text() == "¥238.46"
        geo = popup.geometry()
        assert geo.bottom() < anchor.top() + 4, "chip must sit above the pet head"
        assert geo.right() >= anchor.left() and geo.left() <= anchor.right(),             "chip must horizontally overlap the pet"
    finally:
        popup.hide()


def test_income_notification_pops_money(pet_window):
    """WAGE_PROGRESS shows a ¥ chip; privacy mode shows progress only."""
    from decimal import Decimal
    from wage.model import WageBreakdown
    snap = WageBreakdown(date=__import__("datetime").date(2026, 10, 8),
                         status="workday", configured=True, progress=42,
                         base_earned=Decimal("238.46"))
    pet_window._on_wage_progress(snap)
    try:
        assert pet_window._money_popup.text() == "¥238.46"
        pet_window.wage.settings.privacy_mode = True
        pet_window._on_wage_progress(snap)
        assert pet_window._money_popup.text() == "进度 42%"
    finally:
        pet_window.wage.settings.privacy_mode = False
        pet_window._money_popup.hide()


def test_dynamic_anchor_is_cell_sized(pet_window):
    """Regression: the anchor was a sheet-wide absolute union (4341×5388),
    throwing bubbles/panels to mid-screen. It must stay within one cell."""
    if pet_window.dynamic_renderer is None:
        pytest.skip("single mode")
    bbox = pet_window.dynamic_renderer.visible_bbox()
    assert bbox[2] <= 192 and bbox[3] <= 208, \
        f"cell-relative union must fit one cell, got {bbox}"
    rect = pet_window.visible_pet_rect()
    assert rect.width() <= 192 * pet_window.character.scale + 2
    assert rect.height() <= 208 * pet_window.character.scale + 2
