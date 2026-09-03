"""Small, dependency-free PyQt5 modern UI kit used by app dialogs."""

from .dialog import ModernDialog, ModernConfirmDialog, ModernTextInputDialog, ModernTimeDialog
from .titlebar import ModernTitleBar, TitleBar
from .buttons import PrimaryButton, SecondaryButton, DangerButton
from .cards import Card, StatCard, SectionTitle
from .inputs import ModernLineEdit, ModernComboBox, ModernTimeField
from .message import InlineBanner, Toast
from .character_preview import CharacterPreviewWidget

__all__ = [
    "ModernDialog", "ModernConfirmDialog", "ModernTextInputDialog", "ModernTimeDialog", "ModernTitleBar", "TitleBar", "PrimaryButton", "SecondaryButton", "DangerButton",
    "Card", "StatCard", "SectionTitle", "ModernLineEdit", "ModernComboBox",
    "ModernTimeField", "InlineBanner", "Toast", "CharacterPreviewWidget",
]
