#!/usr/bin/env python
"""Short native-renderer process-tree CPU/RSS measurement."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import statistics
import sys
import time
from pathlib import Path

import psutil
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config as config_mod
import destinations
import pocket_service
import reminder_service
from pet_window import PetWindow


def main(duration=30):
    temp = ROOT / ".tmp" / "native-measure"
    temp.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_DIR = temp
    config_mod.CONFIG_FILE = temp / "config.json"
    reminder_service.REMINDERS_FILE = temp / "reminders.json"
    pocket_service.POCKET_FILE = temp / "pocket.json"
    destinations.DESTINATIONS_FILE = temp / "destinations.json"

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = PetWindow(config_mod.Config())
    window.tray_icon.hide()
    window.show()
    process = psutil.Process()
    tracked = {}
    samples = []
    process.cpu_percent(None)
    for child in process.children(recursive=True):
        child.cpu_percent(None)
        tracked[child.pid] = child
    start = time.time()
    while time.time() - start < duration:
        app.processEvents()
        time.sleep(1)
        processes = [process] + process.children(recursive=True)
        cpu = 0.0
        rss = 0
        for item in processes:
            try:
                if item.pid not in tracked:
                    item.cpu_percent(None); tracked[item.pid] = item
                cpu += item.cpu_percent(None)
                rss += item.memory_info().rss
            except psutil.Error:
                pass
        samples.append({"cpu": cpu, "rss_mb": rss / 1024 / 1024, "processes": len(processes)})
    window._quit_app()
    summary = {
        "duration_s": duration,
        "samples": len(samples),
        "avg_cpu_percent": round(statistics.mean(s["cpu"] for s in samples), 2),
        "peak_cpu_percent": round(max(s["cpu"] for s in samples), 2),
        "avg_rss_mb": round(statistics.mean(s["rss_mb"] for s in samples), 1),
        "peak_rss_mb": round(max(s["rss_mb"] for s in samples), 1),
        "max_processes": max(s["processes"] for s in samples),
    }
    output = ROOT / "docs" / "phase16_native_metrics.json"
    output.write_text(json.dumps({"summary": summary, "samples": samples}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
