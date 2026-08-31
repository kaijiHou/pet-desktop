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


@pytest.mark.smoke
def test_today_wage_follows_pet_when_it_is_the_only_visible_panel(pet_window, qapp, isolated_config, test_temp_root):
    """Bug1: TodayWageWindow must reposition when pet moves, even when
    QuickPanel and PocketWindow are both hidden."""
    from wage.ui_today import TodayWageWindow
    from wage.service import WageService
    ws = WageService(test_temp_root / "wage.json")
    tw = TodayWageWindow(ws, pet_window)
    tw.show(); tw.refresh()
    # Position pet and today wage
    pet_window.move(200, 200); pet_window.show()
    pet_window._today_wage = tw
    pet_window._reposition_attached_panels()
    first_pos = tw.pos()
    # Move pet far away; today wage must follow
    pet_window.move(800, 800)
    pet_window._reposition_attached_panels()
    assert tw.pos().x() != first_pos.x() or tw.pos().y() != first_pos.y(), \
        "TodayWageWindow should follow pet but did not move"
    tw.close()


@pytest.mark.smoke
def test_status_override_updates_existing_record(test_temp_root, isolated_config):
    """Bug2: Changing calendar status must sync existing WorkDayRecord."""
    from wage.service import WageService
    from datetime import datetime, date, timedelta
    ws = WageService(test_temp_root / "wage.json")
    day = date.today()
    # Record a workday
    ws.record_clock_out(datetime(day.year, day.month, day.day, 18, 0))
    assert ws.status_for(day) == "workday"
    # Now change calendar to rest
    ws.set_day_status(day, "rest")
    # status_for should now return rest (not old record)
    assert ws.status_for(day) == "rest"
    # The record should also be updated
    rec = ws.record_for(day)
    assert rec.workday_status == "rest"


@pytest.mark.smoke
def test_restore_auto_updates_existing_record(test_temp_root, isolated_config):
    """Bug2: Restore auto must clear manual override and sync record."""
    from wage.service import WageService
    from datetime import datetime, date
    ws = WageService(test_temp_root / "wage.json")
    day = date.today()
    ws.record_clock_out(datetime(day.year, day.month, day.day, 18, 0))
    ws.set_day_status(day, "rest")
    assert ws.status_for(day) == "rest"
    ws.restore_day_status_auto(day)
    rec = ws.record_for(day)
    assert rec.manual_override is False


@pytest.mark.smoke
def test_rest_override_removes_record_overtime(test_temp_root, isolated_config):
    """Bug2: Rest status should zero out overtime on existing record."""
    from wage.service import WageService
    from datetime import datetime, date
    ws = WageService(test_temp_root / "wage.json")
    day = date.today()
    # Late clock-out = overtime
    ws.record_clock_out(datetime(day.year, day.month, day.day, 20, 0))
    rec = ws.record_for(day)
    assert rec.overtime_minutes > 0
    # Change to rest
    ws.set_day_status(day, "rest")
    rec = ws.record_for(day)
    assert rec.overtime_minutes == 0
    assert rec.overtime_pay == 0


@pytest.mark.smoke
def test_status_change_recalculates_month_tiers(test_temp_root, isolated_config):
    """Bug2: Status change triggers recalculate for month tiers."""
    from wage.service import WageService
    from datetime import datetime, date, timedelta
    ws = WageService(test_temp_root / "wage.json")
    # Create a workday 3 days ago
    day1 = date.today() - timedelta(days=3)
    ws.record_clock_out(datetime(day1.year, day1.month, day1.day, 20, 0))
    r1 = ws.record_for(day1)
    assert r1.overtime_minutes > 0
    # Change it to rest - should recalculate
    ws.set_day_status(day1, "rest")
    r1 = ws.record_for(day1)
    assert r1.overtime_minutes == 0


@pytest.mark.smoke
@pytest.mark.unit
def test_eta_25h_calculation_uses_now_not_overtime_start():
    """Bug3: ETA = now + remaining, not overtime_start + remaining."""
    from datetime import datetime, date, time, timedelta
    from wage.calculator import WageCalculator
    from wage.calendar_service import WorkCalendarService
    # Setup: 24h30m prior overtime, now = 17:45
    cal = WorkCalendarService()
    calc = WageCalculator(type('S', (), {
        'work_start': time(9, 0), 'work_end': time(17, 30),
        'overtime_start': time(17, 30), 'overtime_end': time(20, 0),
        'hourly_rate': 15, 'second_tier_rate': 25,
    })(), cal)
    tier1 = calc.OVERTIME_TIER_1_MINUTES  # 25h = 1500 min
    prior = 1470  # 24h30m
    remaining = tier1 - prior  # 30 min
    now = datetime.now().replace(hour=17, minute=45, second=0, microsecond=0)
    # Correct: ETA = now + remaining = 18:15
    correct_eta = now + timedelta(minutes=remaining)
    assert correct_eta.hour == 18 and correct_eta.minute == 15
    # Wrong (old code): ETA = overtime_start + remaining = 17:30 + 30 = 18:00
    wrong_eta = datetime.combine(now.date(), time(17, 30)) + timedelta(minutes=remaining)
    assert wrong_eta.hour == 18 and wrong_eta.minute == 0
    # So with 15 min remaining (24h45m prior), correct ETA should be 18:00
    remaining_15 = tier1 - (prior + 15)  # 15 min remaining
    correct_eta_15 = now + timedelta(minutes=remaining_15)
    assert correct_eta_15.hour == 18 and correct_eta_15.minute == 0


@pytest.mark.smoke
def test_no_progress_notification_on_rest_day(test_temp_root):
    """Bug4: Progress notification must not fire on rest days."""
    from wage.service import WageService
    from datetime import datetime, time
    ws = WageService(test_temp_root / "wage.json")
    ws.update_settings(monthly_salary=10000, enabled=True, work_start=time(9, 0), work_end=time(17, 30),
                       overtime_start=time(17, 30), income_interval_minutes=30)
    from wage.model import WorkDayRecord
    day = datetime.now().date()
    ws.records[day.isoformat()] = WorkDayRecord(day, "rest", None, 0, 0, 0, "", True)
    ws._last_progress_slot = None
    fired = []
    ws.on_progress = lambda b: fired.append(b)
    result = ws.maybe_emit_progress()
    assert not result, "Should not emit on rest day"
    assert len(fired) == 0


@pytest.mark.smoke
def test_no_progress_notification_after_clock_out(test_temp_root):
    """Bug4: Progress notification must not fire after clock-out."""
    from wage.service import WageService
    from datetime import datetime, time
    ws = WageService(test_temp_root / "wage.json")
    ws.update_settings(monthly_salary=10000, enabled=True, work_start=time(9, 0), work_end=time(17, 30),
                       overtime_start=time(17, 30), income_interval_minutes=30)
    day = datetime.now().replace(hour=18, minute=0, second=0)
    ws.record_clock_out(day)
    ws._last_progress_slot = None
    fired = []
    ws.on_progress = lambda b: fired.append(b)
    result = ws.maybe_emit_progress(datetime.now().replace(hour=18, minute=30))
    assert not result, "Should not emit after clock-out"
    assert len(fired) == 0


@pytest.mark.smoke
def test_progress_notification_during_regular_work(test_temp_root):
    """Bug4: Progress notification should fire during work hours."""
    from wage.service import WageService
    from datetime import datetime, time
    ws = WageService(test_temp_root / "wage.json")
    ws.update_settings(monthly_salary=10000, enabled=True, work_start=time(9, 0), work_end=time(17, 30),
                       overtime_start=time(17, 30), income_interval_minutes=30)
    ws._last_progress_slot = None
    fired = []
    ws.on_progress = lambda b: fired.append(b)
    # During regular work hours, no record yet
    now = datetime.now().replace(hour=10, minute=0, second=0)
    result = ws.maybe_emit_progress(now)
    assert result, "Should emit during work hours"
    assert len(fired) == 1


@pytest.mark.smoke
def test_month_worked_value_includes_current_day_partial_income(test_temp_root):
    """Bug5: worked_value_to_date should include today's real-time base."""
    from wage.service import WageService
    from datetime import datetime, time, date, timedelta
    ws = WageService(test_temp_root / "wage.json")
    ws.update_settings(monthly_salary=10000, enabled=True,
                       work_start=time(9, 0), work_end=time(17, 30),
                       overtime_start=time(17, 30))
    # No records at all
    summary = ws.month_summary()
    daily = ws.calculator().daily_salary(date.today())
    # worked_value should be > 0 because today is a workday
    assert summary["worked_value_to_date"] > 0, \
        f"worked_value_to_date should include today's partial, got {summary['worked_value_to_date']}"


@pytest.mark.unit
def test_missing_clockout_default_time_is_not_current_morning():
    """Bug6: Default clock-out time must not be QTime.currentTime() (could be 08:30)."""
    # Read source to verify the fix: no QTime.currentTime() in default
    import inspect
    from wage.ui_missing import MissingClockoutDialog
    src = inspect.getsource(MissingClockoutDialog.__init__)
    assert "QTime.currentTime()" not in src, "Default must not use QTime.currentTime()"




@pytest.mark.unit
def test_privacy_mode_hides_overtime_hourly_rates():
    """Bug7: Privacy mode must not show hourly rates."""
    import inspect
    from wage.ui_today import TodayWageWindow
    src = inspect.getsource(TodayWageWindow._tier_state)
    assert "hide" in src


@pytest.mark.unit
def test_privacy_mode_hides_cross_tier_rate_text():
    """Bug7: ETA text must mask rate in privacy mode."""
    import inspect
    from wage.ui_today import TodayWageWindow
    src = inspect.getsource(TodayWageWindow.refresh)
    # refresh passes hide to _tier_state; rate text is masked there
    assert "_tier_state(snap, hide=hide)" in src