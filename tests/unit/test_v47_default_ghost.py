"""Default ghost atlas has real, distinct semantic frames."""
import hashlib
from pathlib import Path

from PIL import Image


def _frame_bytes(pack, animation, index=0):
    from character_v4.atlas import SpritesheetAtlas
    from character_v4.manifest import CodexPetManifest
    manifest = CodexPetManifest.load(pack); atlas = SpritesheetAtlas(manifest, pack); assert atlas.load()
    frame = atlas.get_frame(animation, index); return bytes(frame.toImage().bits())


def test_default_ghost_frames_are_nonempty_and_distinct(qapp):
    pack = Path("assets/default_dynamic_ghost")
    from character_v4.atlas import SpritesheetAtlas
    from character_v4.manifest import CodexPetManifest
    manifest = CodexPetManifest.load(pack); atlas = SpritesheetAtlas(manifest, pack); assert atlas.load()
    names = ("idle", "waving", "failed", "review")
    hashes = []
    for name in names:
        frame = atlas.get_frame(name, 0); assert frame is not None
        image = frame.toImage(); assert not image.isNull(); assert image.hasAlphaChannel()
        assert image.width() == 192 and image.height() == 208
        hashes.append(hashlib.sha256(image.bits().asstring(image.byteCount())).hexdigest())
    assert len(set(hashes)) == len(hashes)
    assert hashlib.sha256(atlas.get_frame("idle", 0).toImage().bits().asstring(atlas.get_frame("idle", 0).toImage().byteCount())).hexdigest() != hashlib.sha256(atlas.get_frame("idle", 3).toImage().bits().asstring(atlas.get_frame("idle", 3).toImage().byteCount())).hexdigest()
