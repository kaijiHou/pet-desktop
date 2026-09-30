"""Desktop-pet skin system (V5.4 皮肤系统).

One source of truth for every pet-owned popup surface:

  * five preset skins (樱花粉 / 奶油黄 / 薄荷绿 / 天空蓝 / 香芋紫)
  * user-defined skins persisted to data/ui_skins.json
  * active skin id persisted in config ("ui_skin")
  * set_skin() mutates the legacy theme.* and ui.modern.tokens.* module
    globals (so every window constructed afterwards picks the palette up
    with zero refactor), regenerates the app stylesheet, and emits
    skinChanged so long-lived popups can rebuild.

Colors a skin must provide (hand-tuned per preset):
  accent, accent_hover      — primary buttons, focus, money amounts
  bg                        — window/backdrop tint
  card                      — card background
  border                    — card/separator borders
  text, muted               — heading & caption text
  menu_bg, menu_border      — context/tray menu surface
  menu_highlight, menu_highlight_text — hovered menu item
Derived at runtime: accent_pressed, focus_ring, secondary tints.
"""

import json
import logging

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from paths import DATA_DIR

LOGGER = logging.getLogger("pet.ui_skin")

SKINS_FILE = DATA_DIR / "ui_skins.json"

# id: (display name, colors)
PRESETS = {
    "sakura": ("樱花粉", {
        "accent": "#F27BA7", "accent_hover": "#E0679A",
        "bg": "#FFF6FA", "card": "#FFFFFF", "border": "#F8D7E3",
        "text": "#5C3A4A", "muted": "#91516B",
        "menu_bg": "#FFF5F9", "menu_border": "#F6C6D9",
        "menu_highlight": "#FFE3EE", "menu_highlight_text": "#C2497E",
        "amount": "#E05590",
    }),
    "cream": ("奶油黄", {
        "accent": "#F5A623", "accent_hover": "#E09312",
        "bg": "#FFFBF2", "card": "#FFFFFF", "border": "#F3E3C0",
        "text": "#5C4A2E", "muted": "#926A2A",
        "menu_bg": "#FFFAF0", "menu_border": "#F0DCB4",
        "menu_highlight": "#FBEFD3", "menu_highlight_text": "#9A6B12",
        "amount": "#E08A00",
    }),
    "mint": ("薄荷绿", {
        "accent": "#34B78F", "accent_hover": "#2AA37D",
        "bg": "#F2FBF7", "card": "#FFFFFF", "border": "#CDE9DD",
        "text": "#2F4A3E", "muted": "#31705A",
        "menu_bg": "#F3FCF8", "menu_border": "#C4E6D6",
        "menu_highlight": "#D8F3E7", "menu_highlight_text": "#1F7A5C",
        "amount": "#1FA37D",
    }),
    "sky": ("天空蓝", {
        "accent": "#4A90D9", "accent_hover": "#3A7BC4",
        "bg": "#F3F8FD", "card": "#FFFFFF", "border": "#CFE2F3",
        "text": "#2E4258", "muted": "#385D85",
        "menu_bg": "#F4F9FE", "menu_border": "#C6DDF0",
        "menu_highlight": "#DCEDFB", "menu_highlight_text": "#2B6CB0",
        "amount": "#3A7BC4",
    }),
    "taro": ("香芋紫", {
        "accent": "#9B7EDE", "accent_hover": "#8A6BD1",
        "bg": "#F8F5FD", "card": "#FFFFFF", "border": "#E0D5F2",
        "text": "#463A5C", "muted": "#64528A",
        "menu_bg": "#F9F6FE", "menu_border": "#DCD0F0",
        "menu_highlight": "#ECE4FB", "menu_highlight_text": "#6F4FC0",
        "amount": "#8A6BD1",
    }),
}

SKIN_KEYS = ("accent", "accent_hover", "bg", "card", "border", "text", "muted",
             "menu_bg", "menu_border", "menu_highlight", "menu_highlight_text",
             "amount")


class _SkinBus(QObject):
    skinChanged = pyqtSignal(str)


_bus = _SkinBus()
skinChanged = _bus.skinChanged
_active_id = None


def _load_custom_skins() -> dict:
    try:
        raw = json.loads(SKINS_FILE.read_text(encoding="utf-8-sig"))
        skins = raw.get("skins", []) if isinstance(raw, dict) else []
        return {str(s["id"]): (str(s.get("name", s["id"])), {k: str(s[k]) for k in SKIN_KEYS if k in s})
                for s in skins if isinstance(s, dict) and s.get("id")}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def all_skins() -> dict:
    """id -> (display name, colors) for presets + user customs."""
    skins = {k: (name, dict(colors)) for k, (name, colors) in PRESETS.items()}
    skins.update(_load_custom_skins())
    return skins


def active_id() -> str:
    global _active_id
    if _active_id is None:
        from config import Config
        try:
            saved = Config().get("ui_skin", "sakura")
        except Exception:
            saved = "sakura"
        _active_id = saved if saved in all_skins() else "sakura"
    return _active_id


def palette() -> dict:
    """Resolved color dict of the active skin (plus derived shades)."""
    _, colors = all_skins()[active_id()]
    p = dict(colors)
    p["text"] = _darken_for_contrast(p["text"], p["card"])
    p["muted"] = _darken_for_contrast(p["muted"], p["card"])
    accent = QColor(p["accent"])
    p["action_bg"] = _darken_for_contrast(p["accent"], "#FFFFFF")
    p["action_hover"] = _darken_for_contrast(p["accent_hover"], "#FFFFFF")
    p["accent_pressed"] = QColor(p["action_bg"]).darker(115).name()
    p["focus_ring"] = accent.lighter(145).name()
    p["secondary_border"] = p["border"]
    p["section_bg"] = _tint(p["accent"], p["card"], 0.10)
    p["section_border"] = _tint(p["accent"], p["border"], 0.25)
    # Tints must be MOSTLY white — these are card/section backgrounds, so
    # the accent is only a wash. (An earlier version inverted the ratio and
    # painted the wage card near-full accent, drowning the text.)
    p["tint_light"] = _tint(p["accent"], "#FFFFFF", 0.12)
    p["tint_mid"] = _tint(p["accent"], "#FFFFFF", 0.20)
    p["tint_border"] = _tint(p["accent"], "#FFFFFF", 0.38)
    # Secondary text: darker than the caption muted so labels on tinted
    # cards stay readable (the muted tone alone washes out on pink).
    p["text_soft"] = _darken_for_contrast(_tint(p["text"], p["accent"], 0.70), p["section_bg"])
    p["text_soft"] = _darken_for_contrast(p["text_soft"], p["tint_light"])
    p["amount"] = _darken_for_contrast(p["amount"], p["section_bg"])
    return p


def _tint(accent_hex: str, base_hex: str, accent_ratio: float) -> str:
    a, b = QColor(accent_hex), QColor(base_hex)
    mix = QColor(
        round(a.red() * accent_ratio + b.red() * (1 - accent_ratio)),
        round(a.green() * accent_ratio + b.green() * (1 - accent_ratio)),
        round(a.blue() * accent_ratio + b.blue() * (1 - accent_ratio)),
    )
    return mix.name()


def _contrast(a_hex: str, b_hex: str) -> float:
    def luminance(hex_color):
        color = QColor(hex_color)
        channels = (color.redF(), color.greenF(), color.blueF())
        linear = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                  for c in channels)
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    a, b = sorted((luminance(a_hex), luminance(b_hex)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _darken_for_contrast(color: str, background: str) -> str:
    """Keep the skin hue while making foreground text readable."""
    for percent in range(100, -1, -5):
        candidate = _tint(color, "#000000", percent / 100)
        if _contrast(candidate, background) >= 4.5:
            return candidate
    return "#000000"


def _legacy_bridge(p: dict) -> None:
    """Push the palette into the legacy theme.* / tokens.* globals so every
    window constructed after the switch is re-skinned without refactors."""
    import theme
    import ui.modern.tokens as tokens
    theme.BG = p["bg"]
    theme.BG_CARD = p["card"]
    theme.BG_HOVER = p["menu_highlight"]
    theme.BG_SELECTED = p["menu_highlight"]
    theme.BORDER = p["border"]
    theme.BORDER_STRONG = p["border"]
    theme.TEXT = p["text"]
    theme.TEXT_MUTED = p["muted"]
    theme.TEXT_DISABLED = p["muted"]
    theme.ACCENT = p["accent"]
    theme.ACCENT_HOVER = p["accent_hover"]
    theme.MENU_BG = p["menu_bg"]
    theme.MENU_BORDER = p["menu_border"]
    theme.MENU_HIGHLIGHT = p["menu_highlight"]
    theme.MENU_HIGHLIGHT_TEXT = p["menu_highlight_text"]
    tokens.PRIMARY = p["accent"]
    tokens.PRIMARY_HOVER = p["accent_hover"]
    tokens.BG = p["bg"]
    tokens.CARD = p["card"]
    tokens.BORDER = p["border"]
    tokens.TEXT = p["text"]
    tokens.MUTED = p["muted"]


def set_skin(skin_id: str) -> bool:
    """Switch the active skin, persist it, re-skin the app, notify listeners."""
    global _active_id
    skins = all_skins()
    if skin_id not in skins:
        LOGGER.warning("unknown skin %r; keeping %s", skin_id, _active_id)
        return False
    _active_id = skin_id
    from config import Config
    Config().set("ui_skin", skin_id)
    p = palette()
    _legacy_bridge(p)
    LOGGER.info("skin set: %s (%s)", skin_id, skins[skin_id][0])
    app = QApplication.instance()
    if app is not None:
        import theme
        app.setStyleSheet(theme.app_qss())
    skinChanged.emit(skin_id)
    return True


def initialize() -> None:
    """Apply the persisted skin once at startup (before windows are built)."""
    p = palette()
    _legacy_bridge(p)


def build_custom_colors(accent_hex: str, bg_hex: str) -> dict:
    """Derive a full 12-key palette from two user picks (accent + backdrop).

    Everything else is tinted from the accent so the result always looks
    coherent no matter what the user picks.
    """
    accent = QColor(accent_hex)
    bg = QColor(bg_hex)
    text = _tint(accent_hex, "#000000", 0.20)
    muted = _tint(text, accent_hex, 0.70)
    border = _tint(accent_hex, bg_hex, 0.32)
    return {
        "accent": accent.name(),
        "accent_hover": accent.darker(110).name(),
        "bg": bg.name(),
        "card": "#FFFFFF",
        "border": border,
        "text": text,
        "muted": muted,
        "menu_bg": _tint(accent_hex, bg_hex, 0.14),
        "menu_border": _tint(accent_hex, bg_hex, 0.42),
        "menu_highlight": _tint(accent_hex, bg_hex, 0.24),
        "menu_highlight_text": accent.darker(130).name(),
        "amount": accent.darker(108).name(),
    }


def save_custom_skin(name: str, colors: dict) -> str:
    """Persist a user skin; returns its id."""
    skins_doc = {"skins": []}
    try:
        raw = json.loads(SKINS_FILE.read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict) and isinstance(raw.get("skins"), list):
            skins_doc = raw
    except (OSError, ValueError):
        pass
    skin_id = "custom_" + str(abs(hash((name, colors.get("accent")))))[:8]
    entry = {"id": skin_id, "name": name or "我的皮肤"}
    entry.update({k: colors[k] for k in SKIN_KEYS if k in colors})
    skins_doc["skins"] = [s for s in skins_doc["skins"] if s.get("id") != skin_id]
    skins_doc["skins"].append(entry)
    SKINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SKINS_FILE.write_text(json.dumps(skins_doc, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return skin_id
