#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1 baseline tool — resource measurement of the ORIGINAL app.

Method (documented per task §16):
  * psutil samples the WHOLE process tree once per second:
    the main Python process + all children recursively (this captures the
    QtWebEngineProcess/Chromium subprocesses — measuring python.exe alone
    would severely understate RAM).
  * CPU%: psutil cpu_percent(None) non-blocking; each process is warmed up on
    first sight (first sample for a new process reads 0 — slight undercount).
  * A 10s warm-up window after startup is discarded before scenario A.

Scenarios:
  A  idle_1min      : 60s untouched (note: original code falls asleep after
                      ~60s inactivity via _check_idle — that IS baseline behavior)
  B  idle_5min_cont : next 240s (continuation; cumulative 5-min idle window)
  C  animation      : 30s cycling animation groups via the real play_* APIs
  D  ui_dialogs     : 20s with Settings + Chat dialogs open, water reminder fired

Outputs:
  docs/baseline/baseline_process_metrics.json  (raw samples)
  docs/baseline/baseline_process_metrics.txt   (per-scenario stats)

Run:  .venv/Scripts/python.exe scripts/measure_baseline.py   (~6.5 min)
"""

import json
import os
import statistics
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SAMPLE_INTERVAL = 1.0

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication

from config import Config
import pet_window_web

samples = []           # [t, phase, n_procs, rss_mb, cpu_pct]
current_phase = ["warmup"]
stop_flag = threading.Event()
cpu_warmed = set()


def sampler():
    me = psutil.Process(os.getpid())
    t0 = time.time()
    while not stop_flag.is_set():
        try:
            procs = [me] + me.children(recursive=True)
            cpu, rss, alive = 0.0, 0, 0
            for p in procs:
                try:
                    if p.pid not in cpu_warmed:
                        p.cpu_percent(None)   # prime; returns 0 this time
                        cpu_warmed.add(p.pid)
                    cpu += p.cpu_percent(None)
                    rss += p.memory_info().rss
                    alive += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            samples.append([round(time.time() - t0, 2), current_phase[0],
                            alive, round(rss / 1e6, 1), round(cpu, 1)])
        except Exception as e:
            print("sampler error:", e, flush=True)
        time.sleep(SAMPLE_INTERVAL)


def phase_stats(phase):
    rows = [s for s in samples if s[1] == phase]
    if not rows:
        return None
    rss = [r[3] for r in rows]
    cpu = [r[4] for r in rows]
    return {
        "n_samples": len(rows),
        "avg_cpu": round(statistics.mean(cpu), 2),
        "peak_cpu": round(max(cpu), 1),
        "avg_rss_mb": round(statistics.mean(rss), 1),
        "peak_rss_mb": round(max(rss), 1),
        "proc_counts": sorted({r[2] for r in rows}),
    }


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Clippy Desktop Pet")
    app.setQuitOnLastWindowClosed(False)
    config = Config()

    t_start = time.time()
    load_info = {}
    window = pet_window_web.PetWindow(config)
    window.web.page().loadFinished.connect(
        lambda ok: load_info.setdefault("t", round(time.time() - t_start, 2)))
    window.show()

    th = threading.Thread(target=sampler, daemon=True)
    th.start()

    anim_log = []

    def start_phase(name):
        current_phase[0] = name
        print(f"[phase] {name} @ t={time.time()-t_start:.0f}s", flush=True)

    def drive_animations():
        groups = [window.ANIM_TALKING, window.ANIM_ALERT, window.ANIM_WAVE,
                  window.ANIM_WRITING, window.ANIM_SEARCHING, window.ANIM_CONGRATULATE,
                  window.ANIM_LOOK_AROUND, window.ANIM_IDLE]
        idx = [0]
        def step():
            if current_phase[0] != "animation":
                return
            g = groups[idx[0] % len(groups)]
            window.set_state(window.STATE_TALKING, g)
            anim_log.append((round(time.time() - t_start, 1), "set_state", str(g[0])))
            idx[0] += 1
            QTimer.singleShot(1500, step)
        step()

    def open_dialogs():
        try:
            window.set_state(window.STATE_IDLE)
            sd = pet_window_web.SettingsDialog(window.config, window)
            sd.show()
            cd = pet_window_web.ChatDialog(window.ai_engine, window.config, "", window)
            cd.show()
            window.reminder.tick(31 * 60)   # fire water reminder path once
            QTimer.singleShot(18000, lambda: (sd.close(), cd.close()))
        except Exception as e:
            print("dialog phase error:", e, flush=True)

    def finalize():
        stop_flag.set()
        time.sleep(0.2)
        base = REPO / "docs" / "baseline"
        base.mkdir(parents=True, exist_ok=True)
        meta = {
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0],
            "executable": sys.executable,
            "page_load_seconds": load_info.get("t"),
            "sample_interval_s": SAMPLE_INTERVAL,
            "note": ("cpu% = sum of process-tree cpu_percent (main + all children incl. "
                     "QtWebEngineProcess); rss = sum of tree RSS in MB; warm-up window excluded."),
        }
        stats = {}
        for ph in ["idle_1min", "idle_5min_cont", "animation", "ui_dialogs"]:
            stats[ph] = phase_stats(ph)
        payload = {"meta": meta, "stats": stats,
                   "samples": samples, "anim_log": anim_log}
        (base / "baseline_process_metrics.json").write_text(
            json.dumps(payload, indent=1), encoding="utf-8")

        lines = [f"Baseline process-tree metrics — {meta['recorded_at']}",
                 f"page load: {meta['page_load_seconds']}s", ""]
        for ph, st in stats.items():
            lines.append(f"### {ph}")
            if not st:
                lines.append("  NO SAMPLES")
                continue
            lines.append(f"  samples={st['n_samples']}  proc_counts={st['proc_counts']}")
            lines.append(f"  CPU  avg={st['avg_cpu']}%  peak={st['peak_cpu']}%")
            lines.append(f"  RSS  avg={st['avg_rss_mb']} MB  peak={st['peak_rss_mb']} MB")
            lines.append("")
        # cumulative 5-min idle window = idle_1min + idle_5min_cont
        a, b = stats.get("idle_1min"), stats.get("idle_5min_cont")
        if a and b:
            lines.append("### idle_5min (cumulative A+B window)")
            lines.append(f"  CPU  avg={round((a['avg_cpu']*a['n_samples']+b['avg_cpu']*b['n_samples'])/(a['n_samples']+b['n_samples']),2)}%"
                         f"  peak={max(a['peak_cpu'], b['peak_cpu'])}%")
            lines.append(f"  RSS  avg={round((a['avg_rss_mb']*a['n_samples']+b['avg_rss_mb']*b['n_samples'])/(a['n_samples']+b['n_samples']),1)} MB"
                         f"  peak={max(a['peak_rss_mb'], b['peak_rss_mb'])} MB")
        txt = "\n".join(lines)
        (base / "baseline_process_metrics.txt").write_text(txt, encoding="utf-8")
        print("\n" + txt)
        print(f"\nraw -> {base/'baseline_process_metrics.json'}")
        window._quit_app()
        QTimer.singleShot(800, app.quit)

    # Phase schedule (ms from now)
    QTimer.singleShot(10_000, lambda: start_phase("idle_1min"))
    QTimer.singleShot(70_000, lambda: start_phase("idle_5min_cont"))
    QTimer.singleShot(310_000, lambda: (start_phase("animation"), drive_animations()))
    QTimer.singleShot(340_000, lambda: (start_phase("ui_dialogs"), open_dialogs()))
    QTimer.singleShot(362_000, finalize)

    print("[start] measurement run ~6 min; phases: warmup(10s) A(60s) B(240s) C(30s) D(20s)",
          flush=True)
    rc = app.exec_()
    print(f"[exit] app.exec_() returned {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
