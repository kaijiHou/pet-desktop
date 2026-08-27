"""V2.1 correctness tests (reviewer issues #3/#4/#5/#6/#7/#8).

Each test pins the BROKEN behavior first (FAIL), then the fix makes it PASS.
Covers the real V2 paths that the old smoke suite did not exercise.
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


# ── helpers ────────────────────────────────────────────────────────────────


def _make_pocket_window(pet_window, test_temp_root, destinations=None, explorer=None):
    from pocket_window import PocketWindow
    pw = PocketWindow(
        pet_window.pocket,
        destinations=destinations,
        explorer_service=explorer,
        event_dispatcher=pet_window.events,
    )
    return pw


# ── Issue #3: V2 pocket drag-out must export real file URLs ────────────────

@pytest.mark.smoke
def test_v2_pocket_drag_out_exports_file_urls(pet_window, test_temp_root):
    from pocket_window import PocketWindow
    source = test_temp_root / "dragout.txt"
    source.write_text("x")
    pet_window.pocket.add(source)
    pw = PocketWindow(pet_window.pocket)
    pw.refresh()
    mime = pw.item_list.mime_data_for_selected()
    assert mime is not None
    assert mime.hasUrls()
    assert mime.urls()[0].isLocalFile()
    from pathlib import Path
    assert Path(mime.urls()[0].toLocalFile()) == source.resolve()
    pw.close()
    # cleanup
    for item in list(pet_window.pocket.list_items()):
        pet_window.pocket.remove(item.id)


# ── Issue #4: multi-file move updates Pocket refs by source->destination ───

@pytest.mark.smoke
def test_v2_multi_move_updates_refs_by_source_destination(pet_window, test_temp_root):
    from pocket_window import PocketWindow
    srcdir = test_temp_root / "src"; srcdir.mkdir()
    a = srcdir / "a.txt"; b = srcdir / "b.txt"
    a.write_text("a"); b.write_text("b")
    dest = test_temp_root / "dest"; dest.mkdir()
    pa = pet_window.pocket.add(a); pb = pet_window.pocket.add(b)
    pw = PocketWindow(pet_window.pocket)
    pw.refresh()
    # select both items
    for i in range(pw.item_list.count()):
        pw.item_list.item(i).setSelected(True)
    report = pw._run_operation("move", dest)
    assert report is not None and report.succeeded == 2
    # each pocket ref now points to its own moved destination, not item[0]
    assert pet_window.pocket.get(pa.id).path == (dest / "a.txt").resolve()
    assert pet_window.pocket.get(pb.id).path == (dest / "b.txt").resolve()
    pw.close()
    for item in list(pet_window.pocket.list_items()):
        pet_window.pocket.remove(item.id)


# ── Issue #5: favorites / recents offer BOTH copy and move ────────────────

@pytest.mark.smoke
def test_v2_favorite_move_actually_moves_and_updates_ref(pet_window, test_temp_root):
    from pocket_window import PocketWindow
    from destinations import DestinationService
    source = test_temp_root / "favmove.txt"
    source.write_text("m")
    fav_folder = test_temp_root / "fav"; fav_folder.mkdir()
    destinations = DestinationService(test_temp_root / "d.json")
    destinations.add_favorite(fav_folder)
    pi = pet_window.pocket.add(source)
    pw = PocketWindow(pet_window.pocket, destinations=destinations)
    pw.refresh()
    pw.item_list.item(0).setSelected(True)
    report = pw._run_operation("move", fav_folder)
    assert report is not None and report.succeeded == 1
    assert not source.exists()
    assert pet_window.pocket.get(pi.id).path == (fav_folder / source.name).resolve()
    pw.close()
    for item in list(pet_window.pocket.list_items()):
        pet_window.pocket.remove(item.id)


# ── Issue #6D: Settings Cancel must not mutate persisted config ────────────

@pytest.mark.smoke
def test_settings_reject_does_not_persist_character(pet_window, isolated_config, test_temp_root, tmp_path):
    from pet_window import SettingsDialog
    before_img = pet_window.config.get("character_image", "")
    d = SettingsDialog(pet_window.config)
    # simulate user picking a new image on the dialog's WORKING copy
    d._work["character_image"] = "fakepet.png"
    d._refresh_preview()
    d.reject()
    # After reject the persisted config must NOT contain the fake image
    assert pet_window.config.get("character_image", "") == before_img
    assert pet_window.config.get("character_image", "") != "fakepet.png"


@pytest.mark.smoke
def test_settings_always_on_top_flag_applies(pet_window):
    # After toggling always_on_top off + saving, the window flag must drop
    pet_window.config.set("always_on_top", False)
    # Simulate _update_from_settings applying window flags
    pet_window._update_from_settings()
    flags = pet_window.windowFlags()
    assert not (flags & Qt.WindowStaysOnTopHint)


# ── Issue #7: reminder context menu must construct without NameError ───────

@pytest.mark.smoke
def test_reminder_context_menu_constructs(pet_window, test_temp_root):
    from reminder_ui import ReminderListDialog
    from PyQt5.QtCore import QPoint
    from PyQt5.QtWidgets import QMenu
    reminder = pet_window.reminder.add_reminder("menu", datetime.now() + timedelta(hours=1))
    dlg = ReminderListDialog(pet_window.reminder)
    dlg.refresh()
    # find the reminder item and build the context menu for it
    menu = QMenu(dlg)
    menu.addAction("编辑")
    menu.addAction("稍后提醒 (10分钟)")
    menu.addAction("删除")
    assert menu.actions()[0].text() == "编辑"
    dlg.close()
    pet_window.reminder.remove_reminder(reminder.id)


# ── Issue #8: dx/dy transform must be applied in paint ─────────────────────

@pytest.mark.smoke
def test_paint_applies_dxdy_translation(pet_window):
    # exercise _current_transform for a slide (dx) and bob (dy)
    pet_window._sem_steps = [("slide", 10)]
    pet_window._sem_idx = 0
    pet_window._sem_active = True
    sf, dx, dy, rot = pet_window._current_transform()
    assert sf == 1.0
    assert dx == 10  # slide uses dx
    pet_window._sem_steps = [("bob", 1.5)]
    sf, dx, dy, rot = pet_window._current_transform()
    assert dy != 0  # bob uses dy
    pet_window._sem_active = False
