"""Desktop-pet skin system (V5.4 皮肤系统 → V5.8 主题中心).

One source of truth for every pet-owned popup surface:

  * 16 preset themes in two categories — 可爱 (8, mostly light) and
    炫酷 (8, all dark) — hand-tuned against the V5.8 reference pack
    (docs/V58_REFERENCE_MAPPING.md)
  * user-defined skins persisted to data/ui_skins.json
  * active skin id persisted in config ("ui_skin")
  * set_skin() mutates the legacy theme.* and ui.modern.tokens.* module
    globals (so every window constructed afterwards picks the palette up
    with zero refactor), regenerates the app stylesheet, and emits
    skinChanged so long-lived popups can rebuild.

Core colors a skin must provide (hand-tuned per preset):
  accent, accent_hover      — primary buttons, focus, money amounts
  bg                        — window/backdrop tint
  card                      — card background
  border                    — card/separator borders
  text, muted               — heading & caption text
  menu_bg, menu_border      — context/tray menu surface
  menu_highlight, menu_highlight_text — hovered menu item
  amount                    — money figure color
Optional per-preset flavor keys (derived when absent):
  category ("cute"/"cool"), dark (bool),
  hero_top/hero_bottom      — wage-card gradient stops
  primary_top/primary_bottom— primary-button gradient stops
  glow                      — neon edge color (cool themes)
  ok/info/warn/danger       — calendar status colors
  chip                      — folder/reminder chip background
  deco                      — theme emoji used by the quick panel
Derived at runtime (dark-aware): accent_pressed, focus_ring, secondary
tints, action_bg/action_text, section tints, text_soft.
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
    # ── 可爱 ─────────────────────────────────────────────────────────────
    "sakura": ("樱花甜心", {
        "accent": "#F27BA7", "accent_hover": "#E0679A",
        "bg": "#FFF6FA", "card": "#FFFFFF", "border": "#F8D7E3",
        "text": "#5C3A4A", "muted": "#91516B",
        "menu_bg": "#FFF5F9", "menu_border": "#F6C6D9",
        "menu_highlight": "#FFE3EE", "menu_highlight_text": "#C2497E",
        "amount": "#E05590",
        "category": "cute", "dark": False,
        "hero_top": "#FFEDF4", "hero_bottom": "#FFDCE9",
        "primary_top": "#F27BA7", "primary_bottom": "#E05E90",
        "glow": "#F8A8C4", "deco": "🌸",
    }),
    "garden": ("奶油花园", {
        "accent": "#6E9165", "accent_hover": "#5C7F54",
        "bg": "#FEFAF2", "card": "#FFFFFF", "border": "#E3DCC3",
        "text": "#4A4636", "muted": "#8A8465",
        "menu_bg": "#FBF7EA", "menu_border": "#E6DFC8",
        "menu_highlight": "#F2EDD8", "menu_highlight_text": "#55744E",
        "amount": "#55744E",
        "category": "cute", "dark": False,
        "hero_top": "#F3EFDA", "hero_bottom": "#E9E3C7",
        "primary_top": "#6E9165", "primary_bottom": "#587C50",
        "glow": "#A9C49E", "deco": "🌿",
    }),
    "taro": ("月光薰衣草", {
        "accent": "#9B7EDE", "accent_hover": "#8A6BD1",
        "bg": "#F8F5FD", "card": "#FFFFFF", "border": "#E0D5F2",
        "text": "#463A5C", "muted": "#64528A",
        "menu_bg": "#F9F6FE", "menu_border": "#DCD0F0",
        "menu_highlight": "#ECE4FB", "menu_highlight_text": "#6F4FC0",
        "amount": "#8A6BD1",
        "category": "cute", "dark": False,
        "hero_top": "#F0EAFB", "hero_bottom": "#E3D8F7",
        "primary_top": "#9B7EDE", "primary_bottom": "#8161CE",
        "glow": "#C4AEEF", "deco": "🌙",
    }),
    "sky": ("晴空云朵", {
        "accent": "#4A90D9", "accent_hover": "#3A7BC4",
        "bg": "#F3F8FD", "card": "#FFFFFF", "border": "#CFE2F3",
        "text": "#2E4258", "muted": "#385D85",
        "menu_bg": "#F4F9FE", "menu_border": "#C6DDF0",
        "menu_highlight": "#DCEDFB", "menu_highlight_text": "#2B6CB0",
        "amount": "#3A7BC4",
        "category": "cute", "dark": False,
        "hero_top": "#E8F3FC", "hero_bottom": "#D3E8F9",
        "primary_top": "#4A90D9", "primary_bottom": "#3579C2",
        "glow": "#9CC8EE", "deco": "☁️",
    }),
    "cream": ("蜜桃奶茶", {
        "accent": "#C98A4B", "accent_hover": "#B4763C",
        "bg": "#FFFBF2", "card": "#FFFFFF", "border": "#EFDFC8",
        "text": "#5C4A2E", "muted": "#8A6A45",
        "menu_bg": "#FFFAF0", "menu_border": "#F0E0C4",
        "menu_highlight": "#F9EEDC", "menu_highlight_text": "#96622A",
        "amount": "#A96A2E",
        "category": "cute", "dark": False,
        "hero_top": "#FAF0DC", "hero_bottom": "#F4E2C2",
        "primary_top": "#C98A4B", "primary_bottom": "#A96F35",
        "glow": "#E5C296", "deco": "🍑",
    }),
    "forest": ("森系童话", {
        "accent": "#4E7A46", "accent_hover": "#406839",
        "bg": "#FCF6EA", "card": "#FFFFFF", "border": "#E2D9BE",
        "text": "#454A34", "muted": "#7A7D5E",
        "menu_bg": "#FAF4E4", "menu_border": "#E4DBC0",
        "menu_highlight": "#EDF0D3", "menu_highlight_text": "#3F6A38",
        "amount": "#3F6A38",
        "category": "cute", "dark": False,
        "hero_top": "#EDF1D4", "hero_bottom": "#DFE7BC",
        "primary_top": "#4E7A46", "primary_bottom": "#3C6335",
        "glow": "#9DBE8E", "deco": "🍄",
    }),
    "mint": ("柠檬薄荷", {
        "accent": "#34B78F", "accent_hover": "#2AA37D",
        "bg": "#F2FBF7", "card": "#FFFFFF", "border": "#CDE9DD",
        "text": "#2F4A3E", "muted": "#31705A",
        "menu_bg": "#F3FCF8", "menu_border": "#C4E6D6",
        "menu_highlight": "#D8F3E7", "menu_highlight_text": "#1F7A5C",
        "amount": "#1FA37D",
        "category": "cute", "dark": False,
        "hero_top": "#E5F7EE", "hero_bottom": "#CFEFE1",
        "primary_top": "#34B78F", "primary_bottom": "#259874",
        "glow": "#8CDDBE", "deco": "🍋",
    }),
    "berry_night": ("玫瑰莓夜", {
        "accent": "#E88A96", "accent_hover": "#DE7686",
        "bg": "#331B28", "card": "#4A2637", "border": "#6E3B50",
        "text": "#F7E6EC", "muted": "#D2A3B2",
        "menu_bg": "#402130", "menu_border": "#633349",
        "menu_highlight": "#573042", "menu_highlight_text": "#F2B8C6",
        "amount": "#F2A9B8",
        "category": "cute", "dark": True,
        "hero_top": "#58293E", "hero_bottom": "#3E1F2F",
        "primary_top": "#E88A96", "primary_bottom": "#C05A70",
        "glow": "#F2A9B8", "deco": "🌹",
    }),
    # ── 炫酷 ─────────────────────────────────────────────────────────────
    "cyber_night": ("暗夜赛博", {
        "accent": "#3FA9F5", "accent_hover": "#5FC0FF",
        "bg": "#0C1625", "card": "#14233A", "border": "#22405F",
        "text": "#E6F2FF", "muted": "#8FB0CC",
        "menu_bg": "#101D30", "menu_border": "#1E3A57",
        "menu_highlight": "#17304C", "menu_highlight_text": "#7CC8FF",
        "amount": "#4FC3FF",
        "category": "cool", "dark": True,
        "hero_top": "#17304F", "hero_bottom": "#0F1D31",
        "primary_top": "#2E8FE0", "primary_bottom": "#1F6CB0",
        "glow": "#37B6FF", "deco": "🤖",
    }),
    "deep_pulse": ("深海脉冲", {
        "accent": "#2E9BE6", "accent_hover": "#4FB2F5",
        "bg": "#011A3A", "card": "#062C55", "border": "#10497F",
        "text": "#E0F2FF", "muted": "#7FA8CC",
        "menu_bg": "#052450", "menu_border": "#0D4276",
        "menu_highlight": "#0A3B6E", "menu_highlight_text": "#6FC2FF",
        "amount": "#58C7FF",
        "category": "cool", "dark": True,
        "hero_top": "#0A3A6B", "hero_bottom": "#04234A",
        "primary_top": "#2585D4", "primary_bottom": "#16629F",
        "glow": "#2FB4FF", "deco": "🐋",
    }),
    "ember_tech": ("赤焰机能", {
        "accent": "#E23B3B", "accent_hover": "#F05555",
        "bg": "#0F0E11", "card": "#1C1418", "border": "#472A30",
        "text": "#F5EDED", "muted": "#B59AA0",
        "menu_bg": "#171216", "menu_border": "#3A2226",
        "menu_highlight": "#2A1A1E", "menu_highlight_text": "#FF8A8A",
        "amount": "#FF6B6B",
        "category": "cool", "dark": True,
        "hero_top": "#2A1720", "hero_bottom": "#190F15",
        "primary_top": "#C93232", "primary_bottom": "#9E2020",
        "glow": "#FF4444", "deco": "🔥",
    }),
    "aurora_pulse": ("极光脉冲", {
        "accent": "#4F8DF9", "accent_hover": "#6FA5FF",
        "bg": "#0A122A", "card": "#152551", "border": "#26468C",
        "text": "#E8F0FF", "muted": "#8FA6D9",
        "menu_bg": "#11204A", "menu_border": "#23407E",
        "menu_highlight": "#1B3468", "menu_highlight_text": "#86B4FF",
        "amount": "#6FB6FF",
        "category": "cool", "dark": True,
        "hero_top": "#1B3C7A", "hero_bottom": "#101F42",
        "primary_top": "#3F7BE8", "primary_bottom": "#2C5AB8",
        "glow": "#4FA0FF", "deco": "🛰️",
    }),
    "titanium": ("钛灰锋芒", {
        "accent": "#7FA8D9", "accent_hover": "#97BCE6",
        "bg": "#171D25", "card": "#232C39", "border": "#38455A",
        "text": "#E8EEF5", "muted": "#9AAABB",
        "menu_bg": "#1D2530", "menu_border": "#333F4D",
        "menu_highlight": "#2A3542", "menu_highlight_text": "#B4D2F0",
        "amount": "#A9C9EC",
        "category": "cool", "dark": True,
        "hero_top": "#2C3949", "hero_bottom": "#1E2733",
        "primary_top": "#6C97C9", "primary_bottom": "#4F79A8",
        "glow": "#6FA0D8", "deco": "⚙️",
    }),
    "obsidian_gold": ("黑曜流光", {
        "accent": "#E8C268", "accent_hover": "#F2D284",
        "bg": "#0A0908", "card": "#1C1712", "border": "#42351F",
        "text": "#F5EFE2", "muted": "#B9AD92",
        "menu_bg": "#161210", "menu_border": "#382E1E",
        "menu_highlight": "#292112", "menu_highlight_text": "#F2D284",
        "amount": "#F2CE74",
        "category": "cool", "dark": True,
        "hero_top": "#332713", "hero_bottom": "#1E160C",
        "primary_top": "#D4AC4E", "primary_bottom": "#A88634",
        "glow": "#E8B84A", "deco": "🏆",
    }),
    "storm_volt": ("风暴电光", {
        "accent": "#C8F542", "accent_hover": "#D8FA6E",
        "bg": "#06111B", "card": "#10222F", "border": "#25424E",
        "text": "#EAF6E8", "muted": "#93AFA6",
        "menu_bg": "#0D1B24", "menu_border": "#1F3A2A",
        "menu_highlight": "#1A3020", "menu_highlight_text": "#D8FA6E",
        "amount": "#D8FA6E",
        "category": "cool", "dark": True,
        "hero_top": "#1A3320", "hero_bottom": "#0C1D14",
        "primary_top": "#AED935", "primary_bottom": "#86AC1E",
        "glow": "#C8F542", "deco": "⚡",
    }),
    "midnight_neon": ("午夜霓虹", {
        "accent": "#7C5CFF", "accent_hover": "#9678FF",
        "bg": "#050719", "card": "#12103A", "border": "#2E2775",
        "text": "#ECE8FF", "muted": "#A098D6",
        "menu_bg": "#0D0B2E", "menu_border": "#262060",
        "menu_highlight": "#1B174E", "menu_highlight_text": "#B4A2FF",
        "amount": "#B48CFF",
        "category": "cool", "dark": True,
        "hero_top": "#221B5E", "hero_bottom": "#120E36",
        "primary_top": "#6A4AE8", "primary_bottom": "#4F33BE",
        "glow": "#9C6CFF", "deco": "🌌",
    }),
}

SKIN_KEYS = ("accent", "accent_hover", "bg", "card", "border", "text", "muted",
             "menu_bg", "menu_border", "menu_highlight", "menu_highlight_text",
             "amount")

CATEGORIES = ("cute", "cool")


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


def skins_by_category(category: str) -> dict:
    """Preset skins of one product category (可爱 / 炫酷), in declared order."""
    return {sid: (name, colors) for sid, (name, colors) in PRESETS.items()
            if colors.get("category") == category}


def category_of(skin_id: str) -> str:
    colors = all_skins().get(skin_id, (None, {}))[1]
    return colors.get("category", "cute")


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
    return resolve_palette(colors)


def resolve_palette(colors: dict) -> dict:
    """Derive the full token set from a skin's core colors (dark-aware)."""
    p = dict(colors)
    dark = bool(colors.get("dark", False))
    p["dark"] = dark
    p["category"] = colors.get("category", "cute")
    p["tint_base"] = p["card"] if dark else "#FFFFFF"

    p["text"] = _fit_text(p["text"], p["card"])
    p["muted"] = _fit_text(p["muted"], p["card"])
    accent = QColor(p["accent"])
    p["section_bg"] = _tint(p["accent"], p["card"], 0.10)
    p["section_border"] = _tint(p["accent"], p["border"], 0.25)
    # Tints must stay MOSTLY card-colored — they are washes, not fills. (An
    # early version inverted the ratio and drowned the card text.)
    p["tint_light"] = _tint(p["accent"], p["tint_base"], 0.12)
    p["tint_mid"] = _tint(p["accent"], p["tint_base"], 0.20)
    p["tint_border"] = _tint(p["accent"], p["tint_base"], 0.38)
    p["text_soft"] = _fit_text(_tint(p["text"], p["accent"], 0.70), p["section_bg"])
    p["text_soft"] = _fit_text(p["text_soft"], p["tint_light"])
    # Primary action: bright accents (lime/gold/vivid pink) get dark text on
    # the raw hue; mid-tone accents keep white text on a contrast-darkened fill.
    if _luminance(p["accent"]) >= 0.42 and _contrast("#141414", p["accent"]) >= 4.5:
        p["action_bg"] = p["accent"]
        p["action_text"] = "#141414"
        p["action_hover"] = QColor(p["accent_hover"]).darker(106).name()
    else:
        p["action_bg"] = _darken_for_contrast(p["accent"], "#FFFFFF")
        p["action_text"] = "#FFFFFF"
        p["action_hover"] = _darken_for_contrast(p["accent_hover"], "#FFFFFF")
    p["accent_pressed"] = QColor(p["action_bg"]).darker(115).name()
    p["focus_ring"] = accent.lighter(145).name() if not dark else accent.lighter(125).name()
    p["secondary_border"] = p["border"]
    # Tints must stay MOSTLY card-colored — they are washes, not fills. (An
    # early version inverted the ratio and drowned the card text.)
    p["tint_light"] = _tint(p["accent"], p["tint_base"], 0.12)
    p["tint_mid"] = _tint(p["accent"], p["tint_base"], 0.20)
    p["tint_border"] = _tint(p["accent"], p["tint_base"], 0.38)
    p["amount"] = _fit_text(p["amount"], p["section_bg"])
    # Flavor keys with derived fallbacks.
    p.setdefault("hero_top", _tint(p["accent"], p["card"], 0.16))
    p.setdefault("hero_bottom", _tint(p["accent"], p["card"], 0.30))
    p.setdefault("primary_top", p["accent"])
    p.setdefault("primary_bottom", p["accent_hover"])
    p.setdefault("glow", p["accent"] if dark else p["border"])
    p.setdefault("deco", "🎀")
    status_defaults = ({"ok": "#4ADE9C", "info": "#58B6FF", "warn": "#FFC24D", "danger": "#FF6B6B"}
                       if dark else
                       {"ok": "#2E8B57", "info": "#3A7BC4", "warn": "#C77700", "danger": "#CC4B4B"})
    for key, default in status_defaults.items():
        p.setdefault(key, default)
    p.setdefault("chip", _tint(p["accent"], p["card"], 0.12) if dark else p["bg"])
    for key in ("ok", "info", "warn", "danger"):
        p[key] = _fit_text(p[key], p["section_bg"])
    return p


def _tint(accent_hex: str, base_hex: str, accent_ratio: float) -> str:
    a, b = QColor(accent_hex), QColor(base_hex)
    mix = QColor(
        round(a.red() * accent_ratio + b.red() * (1 - accent_ratio)),
        round(a.green() * accent_ratio + b.green() * (1 - accent_ratio)),
        round(a.blue() * accent_ratio + b.blue() * (1 - accent_ratio)),
    )
    return mix.name()


def _luminance(hex_color) -> float:
    color = QColor(hex_color)
    channels = (color.redF(), color.greenF(), color.blueF())
    linear = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels)
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def _contrast(a_hex: str, b_hex: str) -> float:
    a, b = sorted((_luminance(a_hex), _luminance(b_hex)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _fit_text(color: str, background: str) -> str:
    """Keep the hue while making foreground text readable in EITHER direction."""
    if _contrast(color, background) >= 4.5:
        return color
    toward_white = _luminance(background) < 0.42
    for percent in range(5, 101, 5):
        candidate = _tint(color, "#FFFFFF" if toward_white else "#000000", percent / 100)
        if _contrast(candidate, background) >= 4.5:
            return candidate
    return "#FFFFFF" if toward_white else "#000000"


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
    tokens.PRIMARY = p["action_bg"]
    tokens.PRIMARY_HOVER = p["action_hover"]
    tokens.BG = p["bg"]
    tokens.CARD = p["card"]
    tokens.BORDER = p["border"]
    tokens.TEXT = p["text"]
    tokens.MUTED = p["muted"]
    tokens.SURFACE = p["menu_bg"]
    tokens.SURFACE_BORDER = p["menu_border"]
    tokens.HOVER_BG = p["menu_highlight"]
    tokens.INPUT_BG = p["menu_bg"]
    tokens.FOCUS_RING = p["focus_ring"]
    tokens.ACTION_TEXT = p["action_text"]
    tokens.SUCCESS = p["ok"]
    tokens.WARNING = p["warn"]
    tokens.DANGER = p["danger"]


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


def build_custom_colors(accent_hex: str, bg_hex: str, dark: bool = False) -> dict:
    """Derive a full 12-key palette from two user picks (accent + backdrop).

    Everything else is tinted from the accent so the result always looks
    coherent no matter what the user picks.
    """
    accent = QColor(accent_hex)
    bg = QColor(bg_hex)
    text = _fit_text(_tint(accent_hex, "#FFFFFF", 0.25) if dark
                     else _tint(accent_hex, "#000000", 0.20),
                     bg_hex if dark else "#FFFFFF")
    muted = _fit_text(_tint(text, accent_hex, 0.70), bg_hex)
    border = _tint(accent_hex, bg_hex, 0.32 if not dark else 0.45)
    menu_bg = _tint(accent_hex, bg_hex, 0.14 if not dark else 0.22)
    return {
        "accent": accent.name(),
        "accent_hover": accent.darker(110).name(),
        "bg": bg.name(),
        "card": _tint(accent_hex, bg_hex, 0.06) if dark else "#FFFFFF",
        "border": border,
        "text": text,
        "muted": muted,
        "menu_bg": menu_bg,
        "menu_border": _tint(accent_hex, bg_hex, 0.42),
        "menu_highlight": _tint(accent_hex, bg_hex, 0.24 if not dark else 0.34),
        "menu_highlight_text": accent.darker(130).name() if not dark else accent.lighter(115).name(),
        "amount": accent.darker(108).name() if not dark else accent.lighter(112).name(),
        "category": "cute",
        "dark": dark,
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
