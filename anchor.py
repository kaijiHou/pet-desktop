"""Unified anchor placement for every pet-attached window.

Single source of truth for BubbleWindow, QuickPanel, PocketWindow and
TodayWageWindow placement, so gaps, screen-edge flips and available-
geometry clamping behave identically everywhere:

  * panels/bubbles anchor to the pet's VISIBLE pixel rect (callers pass
    PetWindow.visible_pet_global_rect(), never the transparent frame)
  * panel gap target: 8–12 px (PANEL_GAP = 8)
  * bubble gap target: 4–10 px (BubbleWindow.GAP = 7)
"""

from PyQt5.QtWidgets import QApplication

PANEL_GAP = 8


def _screen_for(anchor_rect, screen):
    return (screen or QApplication.screenAt(anchor_rect.center())
            or QApplication.primaryScreen())


def place_panel(window, anchor_rect, screen=None, gap=PANEL_GAP):
    """Place a panel to the right of *anchor_rect*; flip to the left when
    it would leave the screen; clamp into availableGeometry. The caller is
    responsible for adjustSize() and for show()/raise_() semantics."""
    scr = _screen_for(anchor_rect, screen)
    avail = scr.availableGeometry()
    w, h = window.width(), window.height()
    x, y = anchor_rect.right() + gap, anchor_rect.top()
    if x + w - 1 > avail.right():
        x = anchor_rect.left() - w - gap
    if y + h - 1 > avail.bottom():
        y = avail.bottom() - h + 1
    x = max(avail.left(), min(x, avail.right() - w + 1))
    y = max(avail.top(), min(y, avail.bottom() - h + 1))
    window.setGeometry(x, y, w, h)
    return window.geometry()


def place_bubble(window, anchor_rect, screen=None, gap=7, tail_len=8):
    """Pick the first side (above/below/left/right) that fits inside
    availableGeometry and return (x, y, tail). Never overlaps the anchor
    by more than the clamp fallback."""
    scr = _screen_for(anchor_rect, screen)
    avail = scr.availableGeometry()
    w, h = window.width(), window.height()
    candidates = [
        (anchor_rect.left() + (anchor_rect.width() - w) // 2,
         anchor_rect.top() - h - gap, "down"),
        (anchor_rect.left() + (anchor_rect.width() - w) // 2,
         anchor_rect.bottom() + gap, "up"),
        (anchor_rect.right() + gap,
         anchor_rect.top() + (anchor_rect.height() - h) // 2, "left"),
        (anchor_rect.left() - w - gap,
         anchor_rect.top() + (anchor_rect.height() - h) // 2, "right"),
    ]
    for x, y, tail in candidates:
        if (x >= avail.left() and y >= avail.top()
                and x + w - 1 <= avail.right() and y + h - 1 <= avail.bottom()):
            return x, y, tail
    x = max(avail.left(), min(candidates[0][0], avail.right() - w + 1))
    y = max(avail.top(), min(candidates[0][1], avail.bottom() - h + 1))
    return x, y, candidates[0][2]
