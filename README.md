# 📎 Clippy Desktop Pet

A Windows desktop pet application — a Clippy-style paperclip character with private, local reminders.

> **⚠️ Asset Notice**
> This repository does **not** include any character sprites or artwork. You need to provide your own!
> You can use:
> - **Clippy** (Microsoft Office paperclip) — search for `clippy_sheet.png` or use the [clippyjs](https://www.npmjs.com/package/clippyjs) package
> - **Any character you like** — create your own sprite sheet (124×93 px per frame)
>
> Place your sprite sheet at `assets/clippy_sheet.png`.

## ✨ Features

- 🖇️ **Desktop Pet** — always-on-top character that follows you around
- ⏰ **Local Reminders** — choose a date, time, and message; nothing is sent online
- 🎭 **43 Animations** — idle, talking, thinking, searching, waving, sleeping, and more
- 🔊 **Sound Effects** — beeps for reminders and interactions
- 🪟 **Windows 95 / Office 97 Styling** — retro dialog boxes and tooltips

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (tested with 3.11.9)
- **Windows 10/11**

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/clippy-desktop-pet.git
cd clippy-desktop-pet

# Install dependencies
pip install PyQt5 PyQtWebEngine Pillow

# Add your character sprite sheet
# Place your 124×93 frame sprite sheet at: assets/clippy_sheet.png
# (see Asset Notice above)

# Run it!
python main.py
```

## 🎮 Controls

| Action | How |
|--------|-----|
| **Move** | Click & drag |
| **Resize** | Scroll wheel |
| **Greet** | Double-click Clippy |
| **Add a reminder** | Right-click → Add Reminder |
| **Manage reminders** | Right-click → My Reminders |
| **Settings** | Right-click → Settings |
| **Sleep** | Right-click → Settings → "Suruh Clippy Bobo" |
| **Quit** | Right-click → Keluar |

## 🎨 Custom Characters

Want to use your own character instead of Clippy?

1. Create a sprite sheet as a **PNG** with frames arranged in a grid
2. Each frame should be **124×93 pixels** (or update `SPRITE_W`/`SPRITE_H`)
3. Save it as `assets/clippy_sheet.png`
4. Create an `assets/animations.json` with frame positions and durations
   (see existing format for reference — `{ "AnimationName": [[x, y, duration_ms], ...] }`)

The character will automatically use your sprites with all 43 animation slots.

## 📁 Project Structure

```
clippy-desktop-pet/
├── main.py                   # Entry point
├── pet_window_web.py         # Main window + dialogs (WebEngine)
├── config.py                 # Configuration handler
├── reminder_service.py       # Persistent local reminder service
├── reminder_ui.py            # Add/manage reminder dialogs
├── sounds.py                 # Sound effects
├── pet_sprite.py             # Sprite loader (legacy)
├── assets/
│   ├── clippy.html           # Canvas renderer (you provide sprites)
│   ├── clippy_sheet.png      # ⚠️ YOU PROVIDE THIS
│   └── animations.json       # ⚠️ YOU PROVIDE THIS
├── launch_mochi.bat          # Windows launcher
├── Mochi.vbs                 # Silent VBS launcher
└── .gitignore
```

## 📝 Notes

- **Clippy** is a trademark of Microsoft Corporation. This project is not affiliated with or endorsed by Microsoft.
- Sound effects are simple `winsound.Beep()` calls — no external audio files needed.

## 📄 License

MIT — feel free to use, modify, and share!
