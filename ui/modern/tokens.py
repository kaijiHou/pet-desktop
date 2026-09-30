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

def base_qss() -> str:
    """Build the modern-dialog stylesheet from the CURRENT tokens.

    ui_skin mutates these globals on skin switch; dialogs constructed later
    pick the new palette up (call this, not the stale constant)."""
    return f"""
QDialog {{ background: transparent; color: {TEXT}; }}
QFrame#modernCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}
QLabel {{ background: transparent; color: {TEXT}; }}
QLabel#muted, QLabel.muted {{ color: {MUTED}; }}
QLabel#title {{ font-size: 20px; font-weight: 700; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}
QPushButton {{ border: 1px solid transparent; border-radius: 8px; padding: 8px 14px; font-size: 13px; min-height: 22px; }}
QPushButton:focus {{ border: 2px solid #93c5fd; }}
QPushButton#linkButton {{ background: transparent; color: {PRIMARY}; padding: 4px 2px; text-align: left; }}
QPushButton#linkButton:hover {{ color: {PRIMARY_HOVER}; }}
QPushButton#primary {{ background: {PRIMARY}; border-color: {PRIMARY}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER}; }}
QPushButton#primary:pressed {{ background: #1e40af; border-color: #1e40af; padding-top: 9px; padding-bottom: 7px; }}
QPushButton#secondary {{ background: #f1f5f9; border-color: #cbd5e1; color: {TEXT}; }}
QPushButton#secondary:hover {{ background: #e8f1ff; border-color: #93c5fd; color: #1d4ed8; }}
QPushButton#secondary:pressed {{ background: #dbeafe; border-color: {PRIMARY}; padding-top: 9px; padding-bottom: 7px; }}
QPushButton:disabled {{ background: #f3f4f6; border-color: #e5e7eb; color: #9ca3af; }}
QPushButton#danger {{ background: #fee2e2; border-color: #fecaca; color: {DANGER}; }}
QPushButton#danger:hover {{ background: #fecaca; border-color: {DANGER}; }}
QPushButton#danger:pressed {{ background: {DANGER}; color: white; }}
QPushButton[feedback="success"] {{ background: #ecfdf5; border-color: #86efac; color: #047857; font-weight: 600; }}
QPushButton#secondary[feedback="success"], QPushButton#primary[feedback="success"] {{ background: #ecfdf5; border-color: #86efac; color: #047857; font-weight: 600; }}
QPushButton#titleButton {{ background: transparent; color: {TEXT}; font-size: 15px; padding: 0; }}
QPushButton#titleButton:hover {{ background: #eef2f7; }}
QLineEdit, QComboBox, QTimeEdit, QDoubleSpinBox, QSpinBox {{ background: #fbfcfe; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 9px; min-height: 22px; }}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border: 1px solid {PRIMARY}; }}
QCheckBox {{ spacing: 8px; }}
"""

# Backwards compatibility: snapshot at import (prefer base_qss()).
BASE_QSS = base_qss()
