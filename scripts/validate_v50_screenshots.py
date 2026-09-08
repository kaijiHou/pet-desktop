"""V5.0 screenshot sanity validation (task §8).

Checks each captured PNG: exists, plausible dimensions, not fully transparent,
not a single solid color, file size above a floor. Not pixel-perfect.
"""

import sys
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = PROJECT / ".tmp" / "v50-acceptance" / "screenshots"

# name -> (min_w, min_h)
REQUIREMENTS = {
    "v50-settings.png": (400, 400),
    "v50-wage-settings.png": (400, 400),
    "v50-calendar-september.png": (800, 550),
    "v50-calendar-october.png": (800, 550),
    "v50-character-gallery.png": (400, 400),
    "v50-character-consistency.png": (400, 300),
}


def validate(directory: Path = DEFAULT_DIR) -> list[tuple[str, bool, str]]:
    results = []
    for name, (min_w, min_h) in REQUIREMENTS.items():
        path = directory / name
        if not path.exists():
            results.append((name, False, "missing"))
            continue
        size = path.stat().st_size
        if size < 5_000:
            results.append((name, False, f"file too small: {size}B"))
            continue
        try:
            img = Image.open(path).convert("RGBA")
        except OSError as exc:
            results.append((name, False, f"unreadable: {exc}"))
            continue
        w, h = img.size
        if w < min_w or h < min_h:
            results.append((name, False, f"{w}x{h} below minimum {min_w}x{min_h}"))
            continue
        alpha = img.getchannel("A")
        if alpha.getextrema()[1] == 0:
            results.append((name, False, "fully transparent"))
            continue
        colors = img.getcolors(maxcolors=65536)
        if colors is not None and len(colors) <= 2:
            results.append((name, False, f"near-single solid color ({len(colors)} distinct)"))
            continue
        results.append((name, True, f"{w}x{h}, {size}B"))
    return results


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    failures = 0
    for name, ok, detail in validate(directory):
        mark = "PASS" if ok else "FAIL"
        print(f"{mark} {name}: {detail}")
        failures += 0 if ok else 1
    print(f"{len(REQUIREMENTS) - failures}/{len(REQUIREMENTS)} screenshots valid")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
