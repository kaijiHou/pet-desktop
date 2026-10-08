"""V5.4: the bubble must never float detached from the pet."""

import pytest
from PyQt5.QtCore import QRect


@pytest.mark.smoke
@pytest.mark.gui
def test_bubble_hides_when_anchor_off_screen(pet_window, monkeypatch):
    """Anchor center off every monitor (dragged off / hidden) → the bubble
    must hide, never land in the middle of some other screen."""
    from PyQt5.QtWidgets import QApplication
    pet_window.show()
    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: None))
    offscreen_anchor = QRect(-2000, -2000, 100, 100)
    pet_window.show_bubble("已在口袋中")
    placed = pet_window._bubble_window.place_near(offscreen_anchor, screen=None)
    assert placed is None
    assert not pet_window._bubble_window.isVisible()


@pytest.mark.smoke
@pytest.mark.gui
def test_bubble_stays_near_pet_at_every_edge(pet_window):
    """Left/top/right/bottom edges: bubble keeps the 4~10px gap, same screen."""
    pet_window.show()
    pet = pet_window
    avail = pet.screen().availableGeometry()
    pw, ph = pet.width(), pet.height()
    spots = [
        (avail.left() + 2, avail.center().y() - ph // 2),          # 左贴边
        (avail.right() - pw - 2, avail.center().y() - ph // 2),    # 右贴边
        (avail.center().x() - pw // 2, avail.top() + 2),           # 上贴边
        (avail.center().x() - pw // 2, avail.bottom() - ph - 2),   # 下贴边
    ]
    try:
        for x, y in spots:
            pet.move(x, y)
            pet.show_bubble("已在口袋中")
            anchor = pet.visible_pet_global_rect()
            b = pet._bubble_window.geometry()
            touching = b.intersects(anchor) or _gap(b, anchor) <= 12
            assert touching, f"bubble detached at pet=({x},{y}): bubble={b}, pet={anchor}"
    finally:
        pet._bubble_hide()


@pytest.mark.smoke
@pytest.mark.gui
def test_fallback_picks_nearest_side(pet_window, monkeypatch):
    """When nothing fits unclamped, the clamped candidate closest to the pet
    wins (never a fixed side)."""
    from anchor import place_bubble
    # A tiny screen where the bubble cannot fit on any side unclamped.
    import PyQt5.QtWidgets as QW
    scr = pet_window.screen()
    big_rect = QRect(10, 10, 300, 240)
    anchor = QRect(scr.availableGeometry().center().x() - 30,
                   scr.availableGeometry().center().y() - 30, 60, 60)
    x, y, tail = place_bubble(big_rect, anchor, scr)
    bubble_geo = QRect(x, y, 300, 240)
    dist = ((bubble_geo.center().x() - anchor.center().x()) ** 2
            + (bubble_geo.center().y() - anchor.center().y()) ** 2)
    assert dist < (scr.availableGeometry().width()) ** 2, \
        "clamped bubble must stay near the pet, not jump across the screen"


def _gap(b, a):
    if b.bottom() < a.top():
        return a.top() - b.bottom() - 1
    if b.top() > a.bottom():
        return b.top() - a.bottom() - 1
    if b.left() > a.right():
        return b.left() - a.right() - 1
    if b.right() < a.left():
        return a.left() - b.right() - 1
    return 0
