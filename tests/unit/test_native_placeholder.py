"""Native renderer remains visible without redistributed character art."""

import pytest

from pet_sprite import ClippySprites


@pytest.mark.unit
def test_missing_user_sheet_uses_original_neutral_placeholder(test_temp_root):
    sprites = ClippySprites(test_temp_root / "not-installed.png")
    frame = sprites.get_frame("RestPose", 0, 1)
    assert sprites.using_placeholder is True
    assert frame.size == (124, 93)
    assert frame.getbbox() is not None
