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

BASE_QSS = f"""
QDialog {{ background: transparent; color: {TEXT}; }}
QFrame#modernCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}
QLabel {{ color: {TEXT}; }}
QLabel#muted, QLabel.muted {{ color: {MUTED}; }}
QLabel#title {{ font-size: 20px; font-weight: 700; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}
QPushButton {{ border: 0; border-radius: 8px; padding: 8px 14px; font-size: 13px; min-height: 22px; }}
QPushButton#linkButton {{ background: transparent; color: {PRIMARY}; padding: 4px 2px; text-align: left; }}
QPushButton#linkButton:hover {{ color: {PRIMARY_HOVER}; }}
QPushButton#primary {{ background: {PRIMARY}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: {PRIMARY_HOVER}; }}
QPushButton#secondary {{ background: #eef2f7; color: {TEXT}; }}
QPushButton#danger {{ background: #fee2e2; color: {DANGER}; }}
QLineEdit, QComboBox, QTimeEdit, QDoubleSpinBox, QSpinBox {{ background: #fbfcfe; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 9px; min-height: 22px; }}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border: 1px solid {PRIMARY}; }}
QCheckBox {{ spacing: 8px; }}
"""
