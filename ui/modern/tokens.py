"""Shared visual tokens; kept deliberately small so dialogs stay native Qt."""

BG = "#f5f7fb"
CARD = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
BORDER = "#e5e7eb"
SUCCESS = "#059669"
WARNING = "#d97706"
DANGER = "#dc2626"
# Dark-theme-aware surfaces (pushed by ui_skin._legacy_bridge; light fallbacks).
SURFACE = "#f1f5f9"
SURFACE_BORDER = "#cbd5e1"
HOVER_BG = "#e8f1ff"
INPUT_BG = "#fbfcfe"
FOCUS_RING = "#93c5fd"
ACTION_TEXT = "#ffffff"

def base_qss() -> str:
    """Build the modern-dialog stylesheet from the CURRENT tokens.

    ui_skin mutates these globals on skin switch; dialogs constructed later
    pick the new palette up (call this, not the stale constant)."""
    return f"""
QDialog {{ background: transparent; color: {TEXT}; }}
QFrame#modernCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 18px; }}
QLabel {{ background: transparent; color: {TEXT}; }}
QLabel#muted, QLabel.muted {{ color: {MUTED}; }}
QLabel#title {{ font-size: 20px; font-weight: 700; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}
QPushButton {{ border: 1px solid transparent; border-radius: 11px; padding: 8px 14px; font-size: 13px; min-height: 22px; }}
QPushButton:focus {{ border: 2px solid {FOCUS_RING}; }}
QPushButton#linkButton {{ background: transparent; color: {PRIMARY}; padding: 4px 2px; text-align: left; }}
QPushButton#linkButton:hover {{ color: {PRIMARY_HOVER}; }}
QPushButton#primary {{ background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 {PRIMARY}, stop:1 {PRIMARY_HOVER}); border-color: {PRIMARY_HOVER}; color: {ACTION_TEXT}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER}; }}
QPushButton#primary:pressed {{ background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER}; padding-top: 9px; padding-bottom: 7px; }}
QPushButton#secondary {{ background: {SURFACE}; border-color: {SURFACE_BORDER}; color: {TEXT}; }}
QPushButton#secondary:hover {{ background: {HOVER_BG}; border-color: {FOCUS_RING}; color: {PRIMARY}; }}
QPushButton#secondary:pressed {{ background: {HOVER_BG}; border-color: {PRIMARY}; padding-top: 9px; padding-bottom: 7px; }}
QPushButton:disabled {{ background: {SURFACE}; border-color: {BORDER}; color: {MUTED}; }}
QPushButton#danger {{ background: {SURFACE}; border-color: {DANGER}; color: {DANGER}; }}
QPushButton#danger:hover {{ background: {DANGER}; border-color: {DANGER}; color: {ACTION_TEXT}; }}
QPushButton#danger:pressed {{ background: {DANGER}; color: {ACTION_TEXT}; }}
QPushButton[feedback="success"] {{ background: {SURFACE}; border-color: {SUCCESS}; color: {SUCCESS}; font-weight: 600; }}
QPushButton#secondary[feedback="success"], QPushButton#primary[feedback="success"] {{ background: {SURFACE}; border-color: {SUCCESS}; color: {SUCCESS}; font-weight: 600; }}
QPushButton#titleButton {{ background: transparent; color: {TEXT}; font-size: 15px; padding: 0; }}
QPushButton#titleButton:hover {{ background: {HOVER_BG}; }}
QLineEdit, QComboBox, QTimeEdit, QDoubleSpinBox, QSpinBox {{ background: {INPUT_BG}; border: 1px solid {BORDER}; border-radius: 11px; padding: 7px 9px; min-height: 22px; color: {TEXT}; }}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border: 1px solid {PRIMARY}; }}
QComboBox QAbstractItemView {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 10px; selection-background-color: {PRIMARY}; selection-color: {ACTION_TEXT}; outline: none; }}
QSpinBox {{ selection-background-color: {PRIMARY}; selection-color: {ACTION_TEXT}; }}
QCheckBox {{ spacing: 8px; }}
"""
