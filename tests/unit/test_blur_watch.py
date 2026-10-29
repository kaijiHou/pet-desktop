"""ClickOutsideWatch state machine: press→release edge outside keep-outs,
with a foreign surface under the cursor, fires on_outside exactly once."""

import pytest
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QCursor

from blur_watch import ClickOutsideWatch


class FakeUser32:
    def __init__(self):
        self.down = False

    def GetAsyncKeyState(self, vk):
        return 0x8000 if self.down else 0


@pytest.fixture()
def watch(qapp, monkeypatch):
    import ctypes
    from PyQt5.QtWidgets import QWidget
    fake = FakeUser32()
    monkeypatch.setattr(ctypes, "windll", type("W", (), {"user32": fake})())
    monkeypatch.setattr("blur_watch.QApplication.widgetAt",
                        staticmethod(lambda pos: None))  # foreign surface
    fired = []
    owner = QWidget(); owner.show()
    w = ClickOutsideWatch(owner, lambda: [QRect(100, 100, 200, 200)],
                          lambda: fired.append(1))
    w.start()
    return w, fake, fired


def _tick(w):
    w._poll()


def test_press_release_outside_fires_once(watch):
    w, fake, fired = watch
    fake.down = True; _tick(w)          # press at (10, 10) — outside panel
    fake.down = False; _tick(w)         # release outside
    assert fired == [1]
    assert w._timer.isActive() is False  # watch stops after firing


def test_press_inside_does_not_fire(watch):
    w, fake, fired = watch
    monkey_cursor = pytest.MonkeyPatch()
    monkey_cursor.setattr("blur_watch.QCursor.pos",
                          staticmethod(lambda: QRect(100, 100, 200, 200).center()))
    try:
        fake.down = True; _tick(w)
        fake.down = False; _tick(w)
    finally:
        monkey_cursor.undo()
    assert fired == []


def test_click_on_own_widget_does_not_fire(watch, monkeypatch):
    w, fake, fired = watch
    fake.down = True; _tick(w)
    monkeypatch.setattr("blur_watch.QApplication.widgetAt",
                        staticmethod(lambda pos: object()))  # our widget under cursor
    fake.down = False; _tick(w)
    assert fired == []
