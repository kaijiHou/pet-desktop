"""Unified visual theme — the single source of truth for V2 styling.

Every window/dialog/menu reads fonts, colors, spacing and QSS from here.
No other module may call setStyleSheet with hand-written colors.
"""

from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY = "Microsoft YaHei UI"
FONT_FALLBACK = "Segoe UI"
FONT_SIZE = 9
FONT_SIZE_SMALL = 8
FONT_SIZE_LARGE = 11

def font(size=FONT_SIZE, weight=QFont.Normal):
    f = QFont()
    f.setFamilies([FONT_FAMILY, FONT_FALLBACK])
    f.setPointSize(size)
    f.setWeight(weight)
    return f

# ── Palette (light, low-saturation neutral; Win11 gadget feel) ──────────────
BG            = "#f9f9fb"   # window background
BG_CARD       = "#ffffff"   # card / list background
BG_HOVER      = "#f0f1f4"
BG_SELECTED   = "#e8f0fe"   # soft blue selection
BORDER        = "#e2e3e8"
BORDER_STRONG = "#c9cbd3"
TEXT          = "#1f2023"
TEXT_MUTED    = "#6b6f76"
TEXT_DISABLED = "#a6a9b0"
ACCENT        = "#3574f0"   # primary action blue
ACCENT_HOVER  = "#2b62d9"
ACCENT_TEXT   = "#ffffff"
DANGER        = "#d94040"
DANGER_HOVER  = "#c03333"
SUCCESS       = "#2e8b57"
TOAST_BG      = "#2b2c30"
TOAST_TEXT    = "#f4f4f5"
RADIUS        = 8           # px, cards & buttons
RADIUS_SMALL  = 6
SPACING       = (8, 12, 16, 20)  # canonical spacing scale

# ── QSS builders ────────────────────────────────────────────────────────────
def app_qss() -> str:
    """Global application stylesheet. Apply once on QApplication."""
    return f"""
    QWidget {{
        background: {BG};
        color: {TEXT};
        font-family: "{FONT_FAMILY}", "{FONT_FALLBACK}";
        font-size: {FONT_SIZE}pt;
    }}
    QLabel#muted {{ color: {TEXT_MUTED}; }}
    QLabel#title {{ font-size: {FONT_SIZE_LARGE}pt; font-weight: 600; }}

    QFrame#card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: {RADIUS}px;
    }}

    QPushButton {{
        background: {BG_CARD};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS}px;
        padding: 5px 14px;
    }}
    QPushButton:hover {{ background: {BG_HOVER}; }}
    QPushButton:pressed {{ background: {BG_SELECTED}; }}
    QPushButton:disabled {{ color: {TEXT_DISABLED}; border-color: {BORDER}; }}
    QPushButton#primary {{
        background: {ACCENT}; border: none; color: {ACCENT_TEXT}; font-weight: 600;
    }}
    QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
    QPushButton#primary:disabled {{ background: {BORDER}; color: {TEXT_DISABLED}; }}
    QPushButton#danger {{ color: {DANGER}; }}
    QPushButton#danger:hover {{ background: {DANGER}; color: white; border-color: {DANGER}; }}
    QPushButton#flat {{ border: none; background: transparent; color: {TEXT_MUTED}; padding: 4px 8px; }}
    QPushButton#flat:hover {{ color: {TEXT}; background: {BG_HOVER}; border-radius: {RADIUS_SMALL}px; }}

    QLineEdit, QDateEdit, QTimeEdit, QSpinBox {{
        background: {BG_CARD};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS}px;
        padding: 4px 8px;
    }}
    QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus {{ border-color: {ACCENT}; }}

    QListWidget {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: {RADIUS}px;
        outline: none;
    }}
    QListWidget::item {{ padding: 6px 8px; border-radius: {RADIUS_SMALL}px; }}
    QListWidget::item:selected {{ background: {BG_SELECTED}; color: {TEXT}; }}
    QListWidget::item:hover:!selected {{ background: {BG_HOVER}; }}

    QComboBox {{
        background: {BG_CARD};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS}px;
        padding: 4px 8px;
    }}

    QMenu {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: {RADIUS}px;
        padding: 4px;
    }}
    QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: {RADIUS_SMALL}px; }}
    QMenu::item:selected {{ background: {BG_SELECTED}; }}
    QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

    QSlider::groove:horizontal {{
        height: 4px; background: {BORDER_STRONG}; border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 16px; height: 16px; margin: -7px 0;
        background: {ACCENT}; border-radius: 8px;
    }}

    QCheckBox {{ spacing: 8px; }}
    QScrollBar:vertical {{
        background: transparent; width: 8px; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_STRONG}; border-radius: 4px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """

def apply(app: QApplication):
    app.setFont(font())
    app.setStyleSheet(app_qss())

def muted_label(text):
    from PyQt5.QtWidgets import QLabel
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    lbl.setWordWrap(True)
    return lbl

def title_label(text):
    from PyQt5.QtWidgets import QLabel
    lbl = QLabel(text)
    lbl.setObjectName("title")
    return lbl
