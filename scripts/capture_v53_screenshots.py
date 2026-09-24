"""Capture isolated Qt renderings of the V5.3 favorite-folder surfaces.

These are direct Qt widget renders on the Windows platform plugin; no
top-level window is shown. They are not screenshots of the user's desktop or
proof of native Explorer, mouse, or DPI behavior.
"""

import os
from pathlib import Path
import sys
import time
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = PROJECT_ROOT / ".tmp" / "v53-demo"
OUTPUT = PROJECT_ROOT / "docs" / "screenshots" / "v53"
os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["TEMP"] = str(DEMO_ROOT)
os.environ["TMP"] = str(DEMO_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtWidgets import QApplication

    from destinations import DestinationService
    from favorite_folders_ui import FavoriteFoldersDialog
    from pocket_service import PocketService
    from pocket_window import PocketWindow
    from quick_panel import QuickPanel

    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex[:10]
    data_path = DEMO_ROOT / f"destinations-{run_id}.json"
    pocket_path = DEMO_ROOT / f"pocket-{run_id}.json"
    names = (
        "项目", "工作", "资料", "临时", "毕业论文",
        "2026年无人机跨视角地理定位实验资料", "设计素材", "归档",
    )
    folders = {}
    for name in names:
        folder = DEMO_ROOT / name
        folder.mkdir(exist_ok=True)
        folders[name] = folder

    destinations = DestinationService(data_path)
    favorites = [destinations.add_favorite(folders[name]) for name in names]
    destinations.record_recent(folders["资料"])

    app = QApplication.instance() or QApplication([sys.argv[0]])
    import theme
    theme.apply(app)

    class DemoPet:
        wage = type("Wage", (), {"configured": False})()
        pocket = type("Pocket", (), {"list_items": staticmethod(lambda: [])})()
        reminder = type("Reminder", (), {"list_reminders": staticmethod(lambda: [])})()
        destination_service = destinations

    def capture(widget, filename, *, adjust=True):
        widget.ensurePolished()
        if adjust:
            widget.adjustSize()
        if widget.layout():
            widget.layout().activate()
        deadline = time.monotonic() + 0.35
        while time.monotonic() < deadline:
            app.processEvents()
        image = QPixmap(widget.size())
        image.fill(Qt.transparent)
        widget.render(image)
        if image.isNull() or image.width() < 200 or image.height() < 100:
            raise RuntimeError(f"Qt returned an empty or undersized capture for {filename}")
        path = OUTPUT / filename
        if not image.save(str(path), "PNG"):
            raise RuntimeError(f"Could not save screenshot: {path}")
        print(f"{filename}: {image.width()}x{image.height()} {path.stat().st_size} bytes")
        widget.close()
        app.processEvents()

    panel = QuickPanel(DemoPet(), destinations=destinations)
    capture(panel, "quick-panel-favorites.png")

    manager = FavoriteFoldersDialog(destinations)
    manager.resize(660, 760)
    capture(manager, "favorite-folders.png", adjust=False)

    # Keep the repair example isolated so the missing row is visible without
    # scrolling through the normal eight-item manager example.
    missing_destinations = DestinationService(DEMO_ROOT / f"missing-destinations-{run_id}.json")
    missing_path = DEMO_ROOT / f"待修复-{run_id}"
    missing_path.mkdir()
    missing = missing_destinations.add_favorite(missing_path)
    missing_destinations.rename_favorite(missing.id, "待修复项目")
    missing_path.rmdir()
    manager = FavoriteFoldersDialog(missing_destinations, focus_id=missing.id)
    manager.resize(660, 560)
    capture(manager, "favorite-folders-missing.png", adjust=False)

    pocket = PocketService(pocket_path)
    source = DEMO_ROOT / "口袋示例"
    source.mkdir(exist_ok=True)
    for name in ("方案草稿.docx", "预算表.xlsx", "会议记录.txt"):
        path = source / name
        path.write_text("演示文件，不含真实内容。", encoding="utf-8")
        pocket.add(path)

    class DemoExplorer:
        def current_directory(self):
            return folders["临时"]

    pocket_window = PocketWindow(
        pocket, destinations=destinations, explorer_service=DemoExplorer(),
    )
    pocket_window.resize(760, 580)
    pocket_window._snapshot_explorer()
    capture(pocket_window, "pocket-favorite-targets.png", adjust=False)

    print(f"DemoRoot={DEMO_ROOT}")
    print(f"ScreenshotDir={OUTPUT}")
    print("RealDesktopControl=NOT_USED")


if __name__ == "__main__":
    main()
