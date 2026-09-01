"""V3.1 scale / bubble-safety / panel-dismiss regressions.

Covers the P0 scale root causes found on real Windows:
  * stale V2 config disabled plain wheel → one-shot migration re-enables it
  * plain wheel + Ctrl+wheel + slider all drive the full chain
    (config → character.scale → base_size → window → visible_pet_rect)
  * BubbleWindow is input-transparent (never eats pet wheel/mouse) and has
    NO Python paintEvent (IME re-entrancy fail-fast hardening)
  * QuickPanel closes on click-outside
"""

import json

import pytest
from PyQt5.QtCore import QPoint, QEvent, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QDialogButtonBox


def _wheel_event(pet, ctrl, dy):
    pos = pet.rect().center()
    mods = Qt.ControlModifier if ctrl else Qt.NoModifier
    return QWheelEvent(pos, pet.mapToGlobal(pos), QPoint(0, 0), QPoint(0, dy),
                       Qt.NoButton, mods, Qt.ScrollUpdate, False)


@pytest.fixture()
def scale_guard(pet_window):
    """Snapshot and restore scale-related state around each test."""
    saved_scale = float(pet_window.config.get("pet_scale", 3))
    saved_wheel = pet_window.config.get("wheel_zoom_enabled", True)
    yield pet_window
    pet_window.config.set("wheel_zoom_enabled", saved_wheel)
    pet_window.config.set("pet_scale", saved_scale)
    pet_window.character.set_scale(saved_scale)
    pet_window._resize_to_character()


# ── config migration (root cause of the user-visible wheel regression) ──

def test_legacy_false_wheel_config_migrates_to_true(test_temp_root, monkeypatch):
    import config as config_mod
    cfg_dir = test_temp_root / "cfg"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"
    cfg_file.write_text(json.dumps({"wheel_zoom_enabled": False, "pet_scale": 3.0}),
                        encoding="utf-8")
    monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_file)
    cfg = config_mod.Config()
    assert cfg.get("wheel_zoom_enabled") is True
    assert cfg.get("v31_wheel_migration_done") is True
    stored = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert stored["wheel_zoom_enabled"] is True


def test_wheel_migration_runs_only_once(test_temp_root, monkeypatch):
    import config as config_mod
    cfg_dir = test_temp_root / "cfg"
    cfg_dir.mkdir()
    monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = config_mod.Config()
    cfg.data["v31_wheel_migration_done"] = True
    cfg.data["wheel_zoom_enabled"] = False   # user disabled it after migration
    cfg.save()
    cfg2 = config_mod.Config()
    assert cfg2.get("wheel_zoom_enabled") is False   # must respect the user


# ── full-chain scale metrics ──

def _metrics(pet):
    w, h = pet._current_character_size()
    vpr = pet.visible_pet_rect()
    return (float(pet.config.get("pet_scale")), float(pet.character.scale),
            (w, h), (pet.width(), pet.height()), (vpr.width(), vpr.height()))


def test_plain_wheel_zooms_full_chain(pet_window, scale_guard):
    original = _metrics(pet_window)
    pet_window.config.set("wheel_zoom_enabled", True)
    QApplication_ = pet_window
    from PyQt5.QtWidgets import QApplication
    QApplication.sendEvent(pet_window, _wheel_event(pet_window, ctrl=False, dy=120))
    after = _metrics(pet_window)
    assert after[0] == pytest.approx(original[0] + 0.2)   # config
    assert after[1] == pytest.approx(original[1] + 0.2)   # character.scale
    assert after[2][0] > original[2][0]                   # base_size
    assert after[3][0] > original[3][0]                   # window size
    assert after[4][0] > original[4][0]                   # visible rect (real pixels!)
    assert after[3][0] == after[2][0] + 40 and after[3][1] == after[2][1] + 60


def test_plain_wheel_respects_disabled_setting(pet_window, scale_guard):
    pet_window.config.set("wheel_zoom_enabled", False)
    before = _metrics(pet_window)
    from PyQt5.QtWidgets import QApplication
    QApplication.sendEvent(pet_window, _wheel_event(pet_window, ctrl=False, dy=120))
    assert _metrics(pet_window) == before


def test_ctrl_wheel_always_zooms(pet_window, scale_guard):
    pet_window.config.set("wheel_zoom_enabled", False)
    before = _metrics(pet_window)
    from PyQt5.QtWidgets import QApplication
    QApplication.sendEvent(pet_window, _wheel_event(pet_window, ctrl=True, dy=120))
    after = _metrics(pet_window)
    assert after[0] == pytest.approx(before[0] + 0.1)
    assert after[2][0] > before[2][0]


def test_settings_slider_preview_updates_visible_pixels(pet_window, scale_guard):
    from pet_window import SettingsDialog
    pet_window.config.set("pet_scale", 3.0)
    pet_window.character.set_scale(3.0)
    pet_window._resize_to_character()
    original = _metrics(pet_window)
    dlg = SettingsDialog(pet_window.config, pet_window)
    dlg.scale_slider.setValue(300)
    preview = _metrics(pet_window)
    assert preview[1] == pytest.approx(6.0)
    assert preview[2][0] == original[2][0] * 2          # 6.0 vs 3.0 → double pixels
    assert preview[4][0] > original[4][0]
    dlg._reject()
    restored = _metrics(pet_window)
    assert restored == original


# ── BubbleWindow hardening (IME-crash + input transparency) ──

def test_bubble_window_has_no_python_paintevent(pet_window):
    # A custom Python paintEvent on a transient translucent top-level is the
    # re-entrancy crash carrier on real Windows IME hosts. QLabel's C++
    # painting must do the blitting.
    from bubble_window import BubbleWindow
    assert "paintEvent" not in vars(BubbleWindow)


def test_bubble_window_is_input_transparent(pet_window):
    from PyQt5.QtCore import QRect
    pet_window.show()
    pet_window.show_bubble("已在口袋中")
    bubble = pet_window._bubble_window
    assert bubble.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert not bubble.testAttribute(Qt.WA_InputMethodEnabled)
    flags = bubble.windowFlags()
    assert bool(flags & Qt.WindowTransparentForInput)
    # content actually rendered into the pixmap
    assert not bubble.pixmap().isNull()
    pet_window._bubble_hide()


def test_bubble_gap_target_near_visible_pet(pet_window):
    pet_window.show()
    pet_window.show_bubble("今天已赚 ¥238.46")
    anchor = pet_window.visible_pet_global_rect()
    b = pet_window._bubble_window.geometry()
    if b.bottom() < anchor.top():
        gap = anchor.top() - b.bottom() - 1
    elif b.top() > anchor.bottom():
        gap = b.top() - anchor.bottom() - 1
    elif b.left() > anchor.right():
        gap = b.left() - anchor.right() - 1
    elif b.right() < anchor.left():
        gap = anchor.left() - b.right() - 1
    else:
        gap = -1
    assert 4 <= gap <= 12, f"bubble gap {gap}px outside 4..10 design"
    pet_window._bubble_hide()


# ── QuickPanel click-outside dismiss ──

class _PressEvent(QEvent):
    def __init__(self, gpos):
        super().__init__(QEvent.MouseButtonPress)
        self._g = gpos

    def globalPos(self):
        return self._g


def test_quick_panel_closes_on_click_outside(pet_window):
    from quick_panel import QuickPanel
    pet_window.show()
    pet_window.move(400, 300)
    panel = QuickPanel(pet_window)
    pet_window._quick_panel = panel
    try:
        panel.showNear(pet_window)
        assert panel.isVisible()
        far_away = pet_window.visible_pet_global_rect().topLeft() - QPoint(400, 400)
        panel.eventFilter(panel, _PressEvent(far_away))
        assert not panel.isVisible()
    finally:
        panel.close()
        pet_window._quick_panel = None


def test_quick_panel_stays_for_clicks_on_panel_and_pet(pet_window):
    from quick_panel import QuickPanel
    pet_window.show()
    panel = QuickPanel(pet_window)
    pet_window._quick_panel = panel
    try:
        panel.showNear(pet_window)
        assert panel.isVisible()
        panel.eventFilter(panel, _PressEvent(panel.geometry().center()))
        assert panel.isVisible()
        panel.eventFilter(panel, _PressEvent(pet_window.visible_pet_global_rect().center()))
        assert panel.isVisible()
    finally:
        panel.close()
        pet_window._quick_panel = None
