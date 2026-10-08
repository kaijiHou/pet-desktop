"""File-event bubbles carry the absolute path (title stays when path is None)."""

from types import SimpleNamespace

import pytest


class _ShellEvent:
    def __init__(self, action, path):
        self.action = action
        self.path = path
        self.category = "windows"


@pytest.mark.smoke
@pytest.mark.gui
def test_shell_bubble_includes_absolute_path(pet_window):
    pet_window.config.set("file_event_animations_enabled", True)
    pet_window.show_bubble("", 100)
    pet_window._on_shell_event(_ShellEvent("created", r"D:\work\新建 报告.docx"))
    try:
        text = pet_window._bubble_text
        assert "检测到新建文件" in text
        assert "D:\work\新建 报告.docx" in text
    finally:
        pet_window._bubble_hide()


@pytest.mark.smoke
@pytest.mark.gui
def test_shell_bubble_without_path_keeps_title_only(pet_window):
    pet_window.config.set("file_event_animations_enabled", True)
    pet_window._on_shell_event(_ShellEvent("deleted", None))
    try:
        text = pet_window._bubble_text
        assert "检测到删除文件" in text
        assert "\\" not in text
    finally:
        pet_window._bubble_hide()


@pytest.mark.smoke
@pytest.mark.gui
def test_shell_events_in_project_sandbox_suppressed(pet_window):
    """pytest/probe churn under .tmp must not bubble on the user's desktop."""
    from pathlib import Path
    from paths import TEMP_DIR
    pet_window.config.set("file_event_animations_enabled", True)
    pet_window.show_bubble("", 100)
    sandbox_path = TEMP_DIR / "tests" / "whatever.txt"
    pet_window._on_shell_event(_ShellEvent("deleted", sandbox_path))
    assert pet_window._bubble_text == ""
    assert not pet_window._bubble_window.isVisible()
