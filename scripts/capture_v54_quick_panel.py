"""Capture an isolated render of the redesigned V5.4 QuickPanel."""

import os
from pathlib import Path
import sys
import time
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = PROJECT_ROOT / ".tmp" / "v54-quick-panel-demo"
OUTPUT = PROJECT_ROOT / "docs" / "screenshots" / "v54"
os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["TEMP"] = str(DEMO_ROOT)
os.environ["TMP"] = str(DEMO_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtWidgets import QApplication

    from destinations import DestinationService
    from quick_panel import QuickPanel

    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex[:10]
    destinations = DestinationService(DEMO_ROOT / f"destinations-{run_id}.json")
    for name in ("工作", "资料", "项目"):
        path = DEMO_ROOT / name
        path.mkdir(exist_ok=True)
        destinations.add_favorite(path)

    app = QApplication.instance() or QApplication([sys.argv[0]])
    import theme
    import ui_skin
    ui_skin._active_id = "sakura"  # demo only; never write the user's saved choice
    ui_skin.initialize()
    theme.apply(app)

    class DemoPet:
        wage = type("Wage", (), {"configured": False})()
        pocket = type("Pocket", (), {"list_items": staticmethod(lambda: [])})()
        reminder = type("Reminder", (), {"list_reminders": staticmethod(lambda: [])})()
        destination_service = destinations

    panel = QuickPanel(DemoPet(), destinations=destinations)
    live = "--live" in sys.argv
    if not live:
        panel.setAttribute(Qt.WA_DontShowOnScreen, True)
    else:
        panel.move(100, 100)
        panel.show()
    panel.ensurePolished()
    panel.adjustSize()
    if live:
        panel.resize(320, 480)
    if panel.layout():
        panel.layout().activate()
    deadline = time.monotonic() + 0.25
    while time.monotonic() < deadline:
        app.processEvents()

    if live:
        image = panel.grab()
    else:
        image = QPixmap(panel.size())
        image.fill(Qt.transparent)
        panel.render(image)
    output = OUTPUT / ("v54-skin-contrast-shown-widget-sakura-full.png" if live
                       else "v54-quick-panel-redesign-final.png")
    if image.isNull() or image.width() < 200 or image.height() < 100:
        raise RuntimeError(f"Qt returned an undersized capture: {image.size()}")
    if not image.save(str(output), "PNG"):
        raise RuntimeError(f"Could not save screenshot: {output}")
    print(f"{output.name}: {image.width()}x{image.height()} {output.stat().st_size} bytes")
    panel.close()
    app.processEvents()


if __name__ == "__main__":
    main()
