"""V2.2 interaction regressions.

These tests exercise the production Qt widgets and handlers.  They do not
claim to replace the final Explorer mouse acceptance documented in
``docs/V22_REAL_ACCEPTANCE.md``; the latter is intentionally a separate
black-box check for OLE/UIPI behavior.
"""

from pathlib import Path

import pytest
from PyQt5.QtCore import QPoint, QPointF, QRect, Qt, QUrl
from PyQt5.QtGui import QKeyEvent, QWheelEvent


class DropEvent:
    def __init__(self, urls, proposed=Qt.MoveAction):
        self._urls = urls
        self._proposed = proposed
        self._drop_action = proposed
        self.accepted = False
        self.ignored = False

    def mimeData(self):
        return self

    def formats(self):
        return ["text/uri-list"]

    def hasUrls(self):
        return bool(self._urls)

    def urls(self):
        return self._urls

    def proposedAction(self):
        return self._proposed

    def possibleActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def setDropAction(self, action):
        self._drop_action = action

    def dropAction(self):
        return self._drop_action

    def isAccepted(self):
        return self.accepted

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


def _wheel(angle_y):
    point = QPointF(40, 40)
    return QWheelEvent(point, point, QPoint(0, 0), QPoint(0, angle_y),
                       Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)


def _restore_scale(pet, scale):
    pet.config.set("pet_scale", scale)
    pet.character.set_scale(scale)
    pet._resize_to_character()


@pytest.mark.smoke
@pytest.mark.gui
def test_scale_slider_live_updates_pet_geometry(pet_window):
    from pet_window import SettingsDialog

    original_scale = pet_window.character.scale
    original_size = pet_window.size()
    dialog = SettingsDialog(pet_window.config, pet_window)
    try:
        target = 250 if dialog.scale_slider.value() != 250 else 100
        dialog.scale_slider.setValue(target)
        assert pet_window.character.scale != original_scale
        assert pet_window.size() != original_size
    finally:
        dialog._reject()
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_scale_cancel_restores_original_size(pet_window):
    from pet_window import SettingsDialog

    original_scale = pet_window.character.scale
    original_size = pet_window.size()
    dialog = SettingsDialog(pet_window.config, pet_window)
    dialog.scale_slider.setValue(250 if dialog.scale_slider.value() != 250 else 100)
    dialog._reject()
    assert pet_window.character.scale == original_scale
    assert pet_window.size() == original_size
    assert pet_window.config.get("pet_scale") == original_scale


@pytest.mark.smoke
@pytest.mark.gui
def test_scale_ok_persists(pet_window):
    from pet_window import SettingsDialog

    original_scale = pet_window.character.scale
    dialog = SettingsDialog(pet_window.config, pet_window)
    target = 200 if dialog.scale_slider.value() != 200 else 250
    dialog.scale_slider.setValue(target)
    expected = target / 50.0
    dialog._save()
    try:
        assert pet_window.config.get("pet_scale") == expected
        assert pet_window.character.scale == expected
    finally:
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_mouse_wheel_changes_size(pet_window):
    original_scale = pet_window.character.scale
    original_size = pet_window.size()
    try:
        pet_window.config.set("wheel_zoom_enabled", True)
        pet_window.wheelEvent(_wheel(120))
        assert pet_window.character.scale > original_scale
        assert pet_window.size() != original_size
    finally:
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_scale_clamped_min_and_max(pet_window):
    original_scale = pet_window.character.scale
    try:
        pet_window._change_scale(-100)
        assert pet_window.character.scale == 1.0
        pet_window._change_scale(100)
        assert pet_window.character.scale == 6.0
    finally:
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_drag_enter_forces_copy_action(pet_window, test_temp_root):
    source = test_temp_root / "drag-test.txt"
    source.write_text("payload")
    event = DropEvent([QUrl.fromLocalFile(str(source))])
    pet_window.dragEnterEvent(event)
    assert event.accepted and not event.ignored
    assert event.dropAction() == Qt.CopyAction


@pytest.mark.smoke
@pytest.mark.gui
def test_drag_move_keeps_valid_local_file_accepted(pet_window, test_temp_root):
    source = test_temp_root / "drag-move.txt"
    source.touch()
    event = DropEvent([QUrl.fromLocalFile(str(source))])
    pet_window.dragMoveEvent(event)
    assert event.accepted and event.dropAction() == Qt.CopyAction


@pytest.mark.smoke
@pytest.mark.gui
def test_drop_multiple_files_directory_duplicate_and_remote_rejected(
        pet_window, test_temp_root):
    one = test_temp_root / "one.txt"
    two = test_temp_root / "two.txt"
    folder = test_temp_root / "folder"
    one.write_text("1")
    two.write_text("2")
    folder.mkdir()
    urls = [QUrl.fromLocalFile(str(one)), QUrl.fromLocalFile(str(two)),
            QUrl.fromLocalFile(str(folder))]
    first = DropEvent(urls)
    pet_window.dropEvent(first)
    assert first.accepted and first.dropAction() == Qt.CopyAction
    assert {item.path for item in pet_window.pocket.list_items()} == {
        one.resolve(), two.resolve(), folder.resolve()
    }
    second = DropEvent([QUrl.fromLocalFile(str(one)), QUrl("https://example.com/x")])
    pet_window.dropEvent(second)
    assert second.accepted and len(pet_window.pocket.list_items()) == 3
    assert one.exists() and two.exists() and folder.is_dir()
    for item in list(pet_window.pocket.list_items()):
        pet_window.pocket.remove(item.id)


@pytest.mark.smoke
@pytest.mark.gui
def test_settings_data_and_log_buttons_use_local_urls(pet_window, test_temp_root, monkeypatch):
    import paths
    from pet_window import SettingsDialog
    from PyQt5.QtGui import QDesktopServices

    data_dir = test_temp_root / "data"
    log_dir = test_temp_root / "logs"
    monkeypatch.setattr(paths, "DATA_DIR", data_dir)
    monkeypatch.setattr(paths, "LOG_DIR", log_dir)
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        lambda url: opened.append(url) or True)
    dialog = SettingsDialog(pet_window.config, pet_window)
    try:
        dialog._open_data_dir()
        dialog._open_log_dir()
    finally:
        dialog.close()
    assert [url.isLocalFile() for url in opened] == [True, True]
    assert Path(opened[0].toLocalFile()) == data_dir
    assert Path(opened[1].toLocalFile()) == log_dir


@pytest.mark.smoke
@pytest.mark.gui
def test_quick_panel_close_and_second_pet_click_hides(pet_window):
    from quick_panel import QuickPanel

    panel = QuickPanel(pet_window)
    pet_window._quick_panel = panel
    panel.showNear(pet_window)
    assert panel.isVisible()
    panel.panel_close_btn.click()
    assert not panel.isVisible()
    pet_window._on_single_click()
    assert panel.isVisible()
    pet_window._on_single_click()
    assert not panel.isVisible()
    panel.close()


@pytest.mark.smoke
@pytest.mark.gui
def test_pocket_close_and_escape_hide(pet_window):
    from pocket_window import PocketWindow

    panel = PocketWindow(pet_window.pocket)
    pet_window._pocket_window = panel
    panel.show_near(pet_window.geometry())
    assert panel.isVisible()
    panel.close_btn.click()
    assert not panel.isVisible()
    panel.show_near(pet_window.geometry())
    panel.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape,
                                  Qt.NoModifier))
    assert not panel.isVisible()
    panel.close()
    pet_window._pocket_window = None


@pytest.mark.smoke
@pytest.mark.gui
def test_visible_quick_panel_repositions_when_pet_moves(pet_window):
    from quick_panel import QuickPanel

    original_scale = pet_window.character.scale
    pet_window.character.set_scale(1.0)
    pet_window._resize_to_character()
    panel = QuickPanel(pet_window)
    pet_window._quick_panel = panel
    try:
        pet_window.show()
        pet_window.move(120, 120)
        panel.showNear(pet_window)
        old_panel_pos = panel.pos()
        pet_window.move(pet_window.pos() + QPoint(140, 35))
        assert panel.isVisible()
        assert panel.pos() != old_panel_pos
        anchor = pet_window.visible_pet_global_rect()
        expected_right = anchor.right() + 8
        expected_left = anchor.left() - panel.width() - 8
        assert panel.x() in (expected_right, expected_left)
    finally:
        panel.close()
        pet_window._quick_panel = None
        pet_window.hide()
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_visible_pocket_repositions_when_pet_moves(pet_window):
    from pocket_window import PocketWindow

    original_scale = pet_window.character.scale
    pet_window.character.set_scale(1.0)
    pet_window._resize_to_character()
    panel = PocketWindow(pet_window.pocket)
    pet_window._pocket_window = panel
    try:
        pet_window.show()
        pet_window.move(0, 120)
        panel.show_near(pet_window.geometry())
        old_panel_pos = panel.pos()
        pet_window.move(pet_window.pos() + QPoint(60, 30))
        assert panel.isVisible() and panel.pos() != old_panel_pos
        anchor = pet_window.visible_pet_global_rect()
        expected_right = anchor.right() + 8
        expected_left = anchor.left() - panel.width() - 8
        assert panel.x() in (expected_right, expected_left)
    finally:
        panel.close()
        pet_window._pocket_window = None
        pet_window.hide()
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_anchor_flips_left_near_screen_right_edge(pet_window):
    from quick_panel import QuickPanel

    original_scale = pet_window.character.scale
    pet_window.character.set_scale(1.0)
    pet_window._resize_to_character()
    panel = QuickPanel(pet_window)
    try:
        screen = pet_window.screen()
        avail = screen.availableGeometry()
        anchor = QRect(avail.right() - pet_window.width() + 1,
                       avail.top() + 10, pet_window.width(), pet_window.height())
        panel.move_near(anchor, live=True, screen=screen)
        assert panel.geometry().right() <= anchor.left() - 8
    finally:
        panel.close()
        _restore_scale(pet_window, original_scale)


@pytest.mark.smoke
@pytest.mark.gui
def test_anchor_stays_inside_available_geometry(pet_window, test_temp_root):
    from pocket_window import PocketWindow

    panel = PocketWindow(pet_window.pocket)
    screen = pet_window.screen()
    avail = screen.availableGeometry()
    anchor = QRect(avail.left() - 100, avail.bottom() - 20,
                   pet_window.width(), pet_window.height())
    panel.move_near(anchor, live=True, screen=screen)
    # Normal desktop sizes are larger than the panel; these inequalities also
    # make the intended clamping behavior explicit for the test fixture.
    assert panel.geometry().top() >= avail.top()
    assert panel.geometry().bottom() <= avail.bottom()
    panel.close()
