"""Characterization tests for animation metadata (Phase 2).

Source of truth is the tracked assets/animations.json catalog used by the
native renderer.

Facts pinned here were verified against the actual repo at baseline 1d89c85:
  * 43 animations, 1227 frames total
  * every frame is [x, y, duration] ints, grid-aligned to 124x93 cells
  * exactly ONE frame has duration == 0: IdleSideToSide index 25
  * key animations (EmptyTrash, Save, SendMail, Writing) exist
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIMS_JSON = PROJECT_ROOT / "assets" / "animations.json"

FRAME_W, FRAME_H = 124, 93

# Verified present in the real data at baseline (never assume from memory).
KEY_ANIMATIONS = ["EmptyTrash", "Save", "SendMail", "Writing"]

# Required native-renderer animation groups.
ANIM_GROUPS = {
    "ANIM_IDLE": ["Idle1_1", "IdleAtom", "IdleSideToSide", "RestPose",
                  "IdleFingerTap", "IdleRopePile", "IdleEyeBrowRaise"],
    "ANIM_TALKING": ["Explain", "Alert", "Processing", "Thinking"],
    "ANIM_ALERT": ["Alert", "GetAttention"],
    "ANIM_SLEEP": ["IdleSnooze"],
    "ANIM_THINKING": ["Thinking", "IdleHeadScratch"],
    "ANIM_SEARCHING": ["Searching", "CheckingSomething"],
    "ANIM_WAVE": ["Wave", "Greeting"],
    "ANIM_LOOK": ["LookLeft", "LookRight", "LookUp", "LookDown"],
    "ANIM_WRITING": ["Writing", "Print", "Save"],
    "ANIM_HIDE": ["Hide"],
    "ANIM_CONGRATULATE": ["Congratulate", "GetArtsy"],
}


@pytest.fixture(scope="module")
def anims():
    """Load the exact catalog consumed by pet_sprite.py."""
    return json.loads(ANIMS_JSON.read_text(encoding="utf-8"))


# ── Collection shape ───────────────────────────────────────────────────────

@pytest.mark.unit
class TestAnimationCollection:
    def test_collection_is_nonempty_dict(self, anims):
        assert isinstance(anims, dict)
        assert len(anims) > 0

    def test_animation_count_matches_baseline(self, anims):
        assert len(anims) == 43, (
            f"baseline has 43 animations; got {len(anims)} — "
            "metadata changed since Phase 1"
        )

    def test_total_frame_count_matches_baseline(self, anims):
        total = sum(len(frames) for frames in anims.values())
        assert total == 1227, f"baseline has 1227 frames; got {total}"


# ── Per-frame structural legality ──────────────────────────────────────────

@pytest.mark.unit
class TestFrameStructure:
    def test_every_animation_has_at_least_one_frame(self, anims):
        for name, frames in anims.items():
            assert frames, f"animation {name!r} has no frames"

    def test_every_frame_is_xyz_triple_of_ints(self, anims):
        for name, frames in anims.items():
            for i, f in enumerate(frames):
                assert isinstance(f, list) and len(f) == 3, f"{name}[{i}]: {f}"
                assert all(isinstance(v, int) for v in f), f"{name}[{i}]: {f}"

    def test_frame_coordinates_are_non_negative(self, anims):
        for name, frames in anims.items():
            for i, (x, y, _d) in enumerate(frames):
                assert x >= 0 and y >= 0, f"{name}[{i}] negative coord"

    def test_frame_durations_are_non_negative(self, anims):
        for name, frames in anims.items():
            for i, (_x, _y, d) in enumerate(frames):
                assert d >= 0, f"{name}[{i}] negative duration"

    def test_frames_are_grid_aligned_to_frame_cells(self, anims):
        # The renderer crops 124x93 cells at these offsets; misalignment
        # would show torn frames. Verified true in the real data.
        for name, frames in anims.items():
            for i, (x, y, _d) in enumerate(frames):
                assert x % FRAME_W == 0, f"{name}[{i}] x={x} off grid"
                assert y % FRAME_H == 0, f"{name}[{i}] y={y} off grid"


# ── Duration characterization (upstream data is NOT strictly > 0) ─────────

@pytest.mark.unit
class TestFrameDurations:
    def test_exactly_one_zero_duration_frame_is_characterized(self, anims):
        # Real upstream data contains exactly ONE duration==0 frame:
        # IdleSideToSide index 25 -> [1736, 837, 0]. Characterized, not fixed.
        zeros = [
            (name, i, f)
            for name, frames in anims.items()
            for i, f in enumerate(frames)
            if f[2] == 0
        ]
        assert len(zeros) == 1, f"expected exactly 1 zero-duration frame, got {zeros}"
        name, idx, frame = zeros[0]
        assert name == "IdleSideToSide"
        assert idx == 25
        assert frame == [1736, 837, 0]

    def test_all_other_frames_have_positive_duration(self, anims):
        for name, frames in anims.items():
            for i, (_x, _y, d) in enumerate(frames):
                if name == "IdleSideToSide" and i == 25:
                    continue  # the characterized zero-duration frame
                assert d > 0, f"{name}[{i}] has non-positive duration {d}"


# ── Key animations & group membership ──────────────────────────────────────

@pytest.mark.unit
class TestKeyAnimations:
    @pytest.mark.parametrize("name", KEY_ANIMATIONS)
    def test_key_animation_exists(self, anims, name):
        assert name in anims, f"key animation {name!r} missing"
        assert anims[name], f"key animation {name!r} has no frames"

    def test_every_group_animation_exists(self, anims):
        missing = [
            (group, name)
            for group, names in ANIM_GROUPS.items()
            for name in names
            if name not in anims
        ]
        assert not missing, f"group animations missing from metadata: {missing}"
