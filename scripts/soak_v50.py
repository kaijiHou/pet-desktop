"""V5.0 Fresh EXE soak (>=15 min, task §25).

Launches a freshly extracted DesktopPet.exe, samples RSS/CPU/process count
every 60s, writes a markdown report. Idle scenario (no GUI automation this
round — dialogs not exercised; recorded honestly).

Usage: python scripts/soak_v50.py [--minutes 15] [--exe <path>]
"""

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def sample():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process DesktopPet -ErrorAction SilentlyContinue | "
         "Select-Object Id,@{n='RSS';e={[int]($_.WorkingSet64/1MB)}},@{n='CPU';e={[math]::Round($_.CPU,1)}} "
         "| ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=30)
    txt = out.stdout.strip()
    if not txt:
        return None
    import json
    data = json.loads(txt)
    if isinstance(data, list):
        data = data[0] if data else None
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=15)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--out", default=str(PROJECT / "docs" / "V50_SOAK_REPORT.md"))
    args = parser.parse_args()

    exe = Path(args.exe)
    workdir = exe.parent
    proc = subprocess.Popen([str(exe)], cwd=str(workdir))
    time.sleep(8)
    rows = []
    start = time.time()
    end = start + args.minutes * 60
    while time.time() < end:
        s = sample()
        elapsed = int(time.time() - start)
        if s:
            rows.append((elapsed, s.get("Id"), s.get("RSS"), s.get("CPU")))
            print(f"t+{elapsed//60:02d}:{elapsed%60:02d} pid={s.get('Id')} RSS={s.get('RSS')}MB CPU={s.get('CPU')}s")
        else:
            rows.append((elapsed, None, None, None))
            print(f"t+{elapsed//60:02d}:{elapsed%60:02d} PROCESS GONE")
            break
        time.sleep(60)
    try:
        proc.terminate()
    except OSError:
        pass

    gone = [r for r in rows if r[1] is None]
    rss_values = [r[2] for r in rows if r[2] is not None]
    lines = [
        "# V5.0 Fresh EXE Soak Report",
        "",
        f"- Date: {datetime.now():%Y-%m-%d %H:%M}",
        f"- EXE: `{exe}`",
        f"- Duration: {args.minutes} minutes (idle scenario; no GUI automation this round — dialogs not exercised, recorded honestly)",
        f"- Samples: every 60s; process alive at every sample: {'YES' if not gone else 'NO'}",
        f"- RSS start: {rss_values[0]} MB" if rss_values else "- RSS: n/a",
        f"- RSS end: {rss_values[-1]} MB" if rss_values else "",
        f"- RSS min/max: {min(rss_values)} / {max(rss_values)} MB" if rss_values else "",
        f"- CPU total at final sample: {rows[-1][3]} s" if rows and rows[-1][3] is not None else "",
        f"- Crash count: {len(gone)}",
        "",
        "| t+ | pid | RSS MB | CPU s |",
        "|---|---|---|---|",
    ]
    lines += [f"| {r[0]}s | {r[1]} | {r[2]} | {r[3]} |" for r in rows]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written: {args.out}")


if __name__ == "__main__":
    main()
