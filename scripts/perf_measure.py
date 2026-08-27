"""V2 performance measurement: idle CPU/RAM, single process, no WebEngine."""
import time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil

def measure(pid, duration=60, interval=1.0):
    proc = psutil.Process(pid)
    samples = []
    t0 = time.time()
    while time.time() - t0 < duration:
        try:
            cpu = proc.cpu_percent(interval=interval)
            mem = proc.memory_info().rss / (1024*1024)
            # include children
            children = proc.children(recursive=True)
            for c in children:
                try:
                    cpu += c.cpu_percent()
                    mem += c.memory_info().rss / (1024*1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            samples.append((cpu, mem))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
    if not samples:
        return None
    cpus = [s[0] for s in samples]
    mems = [s[1] for s in samples]
    return {
        "duration_s": duration,
        "samples": len(samples),
        "avg_cpu_pct": round(sum(cpus)/len(cpus), 2),
        "peak_cpu_pct": round(max(cpus), 2),
        "avg_rss_mb": round(sum(mems)/len(mems), 1),
        "peak_rss_mb": round(max(mems), 1),
        "process_count": 1 + len(psutil.Process(pid).children(recursive=True)),
        "has_webengine": any("webengine" in (c.name().lower() if hasattr(c, 'name') else '') for c in psutil.Process(pid).children(recursive=True)),
    }

if __name__ == "__main__":
    import json
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if not pid:
        print("Usage: python perf_measure.py <PID>")
        sys.exit(1)
    result = measure(pid)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Process not found")
