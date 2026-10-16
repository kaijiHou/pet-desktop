"""Desktop-pet skin system (V5.4 皮肤系统 → V5.10 素材主题).

One source of truth for every pet-owned popup surface:

  * hand-tuned presets — the classic five (樱花粉/奶油黄/薄荷绿/天空蓝/香芋紫)
    plus 玫瑰月夜 (V5.10, dark, illustration assets); the 2026-10-15 V5.8
    16-theme batch was rolled back by user decision
  * per-theme image assets in assets/ui_themes/<skin_id>/ are OPTIONAL —
    theme_asset() returns None when absent and surfaces fall back to
    palette/emoji rendering
  * user-defined skins persisted to data/ui_skins.json
  * active skin id persisted in config ("ui_skin"); an id that no longer
    exists falls back to sakura
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
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from paths import DATA_DIR

LOGGER = logging.getLogger("pet.ui_skin")

SKINS_FILE = DATA_DIR / "ui_skins.json"

# Per-theme image assets (V5.10 rose_moon): assets/ui_themes/<skin_id>/<name>.png
ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "ui_themes"


def theme_asset(name: str, skin_id: str = None):
    """Path to a theme image asset (e.g. 'avatar', 'icons/bell'), or None."""
    sid = skin_id or active_id()
    path = ASSETS_DIR / sid / f"{name}.png"
    return path if path.exists() else None

# id: (display name, colors)
PRESETS = {
    # ── 经典五套（V5.4 原始预设，2026-10-15 恢复原名原色）─────────────────
    "sakura": ("樱花粉", {
        "accent": "#F27BA7", "accent_hover": "#E0679A",
        "bg": "#FFF6FA", "card": "#FFFFFF", "border": "#F8D7E3",
        "text": "#5C3A4A", "muted": "#91516B",
        "menu_bg": "#FFF5F9", "menu_border": "#F6C6D9",
        "menu_highlight": "#FFE3EE", "menu_highlight_text": "#C2497E",
        "amount": "#E05590",
        "deco": "🌸",
    }),
    "cream": ("奶油黄", {
        "accent": "#F5A623", "accent_hover": "#E09312",
        "bg": "#FFFBF2", "card": "#FFFFFF", "border": "#F3E3C0",
        "text": "#5C4A2E", "muted": "#926A2A",
        "menu_bg": "#FFFAF0", "menu_border": "#F0DCB4",
        "menu_highlight": "#FBEFD3", "menu_highlight_text": "#9A6B12",
        "amount": "#E08A00",
        "deco": "🌻",
    }),
    "mint": ("薄荷绿", {
        "accent": "#34B78F", "accent_hover": "#2AA37D",
        "bg": "#F2FBF7", "card": "#FFFFFF", "border": "#CDE9DD",
        "text": "#2F4A3E", "muted": "#31705A",
        "menu_bg": "#F3FCF8", "menu_border": "#C4E6D6",
        "menu_highlight": "#D8F3E7", "menu_highlight_text": "#1F7A5C",
        "amount": "#1FA37D",
        "deco": "🌿",
    }),
    "sky": ("天空蓝", {
        "accent": "#4A90D9", "accent_hover": "#3A7BC4",
        "bg": "#F3F8FD", "card": "#FFFFFF", "border": "#CFE2F3",
        "text": "#2E4258", "muted": "#385D85",
        "menu_bg": "#F4F9FE", "menu_border": "#C6DDF0",
        "menu_highlight": "#DCEDFB", "menu_highlight_text": "#2B6CB0",
        "amount": "#3A7BC4",
        "deco": "☁️",
    }),
    "taro": ("香芋紫", {
        "accent": "#9B7EDE", "accent_hover": "#8A6BD1",
        "bg": "#F8F5FD", "card": "#FFFFFF", "border": "#E0D5F2",
        "text": "#463A5C", "muted": "#64528A",
        "menu_bg": "#F9F6FE", "menu_border": "#DCD0F0",
        "menu_highlight": "#ECE4FB", "menu_highlight_text": "#6F4FC0",
        "amount": "#8A6BD1",
        "deco": "🍇",
    }),
    # ── 玫瑰月夜（V5.10，插画素材主题，暗色可爱）──────────────────────────
    "rose_moon": ("玫瑰月夜", {
        "accent": "#F0789F", "accent_hover": "#E0668F",
        "bg": "#331C2B", "card": "#4A2839", "border": "#6E3B52",
        "text": "#F9E8EF", "muted": "#D2A3B2",
        "menu_bg": "#3E2130", "menu_border": "#663649",
        "menu_highlight": "#573042", "menu_highlight_text": "#F5B8C8",
        "amount": "#F7A8C0",
        "category": "cute", "dark": True,
        "hero_top": "#5A2C42", "hero_bottom": "#3A1F30",
        "primary_top": "#E86E9C", "primary_bottom": "#C4507C",
        "glow": "#F2A0BC", "deco": "🌹",
    }),
    # ── 薄荷珍珠（V5.11，插画素材主题，海盐薄荷亮色）──────────────────────
    "mint_pearl": ("薄荷珍珠", {
        "accent": "#4FAF9C", "accent_hover": "#3E9C8A",
        "bg": "#F2FAF7", "card": "#FFFFFF", "border": "#D5EBE2",
        "text": "#2E4A42", "muted": "#5E8A7E",
        "menu_bg": "#F0F8F4", "menu_border": "#CFE8DD",
        "menu_highlight": "#DFF3EA", "menu_highlight_text": "#2E8574",
        "amount": "#2F9C8A",
        "category": "cute",
        "hero_top": "#DFF3EC", "hero_bottom": "#C4E8DC",
        "primary_top": "#4FAF9C", "primary_bottom": "#3B9482",
        "glow": "#A8D8C8", "deco": "🐚",
    }),
    # ── 暗夜赛博（V5.12，插画素材主题，霓虹深色）─────────────────────────
    "cyber_night": ("暗夜赛博", {
        "accent": "#6C79FF", "accent_hover": "#5560E8",
        "bg": "#04061A", "card": "#0D1033", "border": "#262C66",
        "text": "#E8ECFF", "muted": "#8B93C8",
        "menu_bg": "#0A0D38", "menu_border": "#23285E",
        "menu_highlight": "#161A4E", "menu_highlight_text": "#8E9AFF",
        "amount": "#7B87FF",
        "category": "cool", "dark": True,
        "hero_top": "#151A4E", "hero_bottom": "#080B26",
        "primary_top": "#515CE8", "primary_bottom": "#3B44B8",
        "glow": "#5E6CFF", "deco": "🤖",
    }),
    # ── 春日花语书房（V5.12，插画素材主题，暖调亮色）─────────────────────
    "spring_study": ("春日花语", {
        "accent": "#7E8C3F", "accent_hover": "#6C7A33",
        "bg": "#FBF7EC", "card": "#FFFFFF", "border": "#E6DFC4",
        "text": "#4A4632", "muted": "#8A8465",
        "menu_bg": "#F8F4E4", "menu_border": "#E4DCC0",
        "menu_highlight": "#EFEBD2", "menu_highlight_text": "#6C7A33",
        "amount": "#77742F",
        "category": "cute",
        "hero_top": "#F3EDD6", "hero_bottom": "#E9E2C4",
        "primary_top": "#7E8C3F", "primary_bottom": "#66722C",
        "glow": "#C9C68C", "deco": "🌼",
    }),
    # ── 极光冰晶赛博（V5.12，插画素材主题，冰蓝深色）─────────────────────
    "aurora_cyber": ("极光冰晶", {
        "accent": "#6E85E8", "accent_hover": "#8399F2",
        "bg": "#0D1530", "card": "#16224A", "border": "#2C3F7E",
        "text": "#E6EDFF", "muted": "#93A5D9",
        "menu_bg": "#121C3E", "menu_border": "#2A3A72",
        "menu_highlight": "#1D2B5C", "menu_highlight_text": "#9FB2F5",
        "amount": "#8FA0F0",
        "category": "cool", "dark": True,
        "hero_top": "#1D2B5C", "hero_bottom": "#0E1734",
        "primary_top": "#5468D6", "primary_bottom": "#3D4FB0",
        "glow": "#6E85E8", "deco": "❄️",
    }),
    # ── 海盐珍珠梦境（V5.13，插画素材主题，浅色可爱）─────────────────────
    "sea_salt_pearl": ("海盐珍珠梦境", {
        "accent": "#7FAE9A", "accent_hover": "#6C9C87",
        "bg": "#F3F6F0", "card": "#FFFFFF", "border": "#DCE6DA",
        "text": "#3E4A42", "muted": "#7E8C82",
        "menu_bg": "#EFF4EC", "menu_border": "#D5E2D2",
        "menu_highlight": "#E2EDE0", "menu_highlight_text": "#5C8C78",
        "amount": "#5C8C78",
        "category": "cute",
        "hero_top": "#E9F2E6", "hero_bottom": "#DCE9DA",
        "primary_top": "#7FAE9A", "primary_bottom": "#5F917C",
        "glow": "#BCD8C8", "deco": "🐚",
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
    # Scrim for text-over-illustration layers (readability on hero art).
    p["scrim_left"] = _rgba(p["bg"], 235)
    p["scrim_mid"] = _rgba(p["bg"], 150)
    p["scrim_right"] = _rgba(p["bg"], 30)
    for key in ("ok", "info", "warn", "danger"):
        p[key] = _fit_text(p[key], p["section_bg"])
    return p


def _rgba(hex_color: str, alpha: int) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


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
