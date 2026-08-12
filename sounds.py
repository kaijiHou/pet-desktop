"""
Sound effects for Clippy Desktop Pet.
Uses winsound for simple beeps and can play Clippy MP3 sounds.
"""

import os
import threading
from pathlib import Path

SOUNDS_DIR = Path(__file__).parent / "assets" / "sounds"


def _play_sound(sound_id):
    """Play a Clippy MP3 sound by ID (1-15) in a background thread."""
    try:
        import winsound
        mp3_path = SOUNDS_DIR / f"clippy_{sound_id}.mp3"
        # winsound only supports WAV, but we can try the system's default
        # MP3 player via PlaySound with SND_ALIAS or SND_FILENAME
        if mp3_path.exists():
            # On Windows 10+, PlaySound can sometimes handle MP3
            winsound.PlaySound(str(mp3_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        # Fall back to beep
        _beep(800, 100)


def _beep(freq=800, duration=150):
    """Play a simple beep."""
    try:
        import winsound
        winsound.Beep(freq, duration)
    except Exception:
        pass


# ─── Event Sounds ───

def play_water_reminder():
    """Play water reminder sound - cheerful double beep."""
    threading.Thread(target=_water_beep, daemon=True).start()

def _water_beep():
    try:
        import winsound
        winsound.Beep(880, 120)
        import time
        time.sleep(0.12)
        winsound.Beep(1100, 200)
    except:
        pass


def play_alert():
    """Alert/exclamation sound."""
    threading.Thread(target=_alert_beep, daemon=True).start()

def _alert_beep():
    try:
        import winsound
        winsound.Beep(440, 200)
        import time
        time.sleep(0.2)
        winsound.Beep(330, 300)
    except:
        pass


def play_startup():
    """Startup jingle."""
    threading.Thread(target=_startup_beep, daemon=True).start()

def _startup_beep():
    try:
        import winsound
        for f in [523, 659, 784, 1047]:
            winsound.Beep(f, 100)
            import time
            time.sleep(0.06)
    except:
        pass
