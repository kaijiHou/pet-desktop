"""Character V4 — Animated Pet Pack System.

Codex/Petdex compatible dynamic character renderer with state machine.
"""
from .manifest import CodexPetManifest, ValidationResult, CODEX_V1_ROWS, CODEX_V2_ROWS
from .atlas import SpritesheetAtlas
from .animation import AnimationPlayer
from .state_machine import PetStateMachine, DEFAULT_STATES
from .renderer import DynamicPackRenderer
from .importer import import_codex_pack, scan_codex_home
from .default_pet import generate_default_pet

__all__ = [
    "CodexPetManifest", "ValidationResult",
    "SpritesheetAtlas", "AnimationPlayer",
    "PetStateMachine", "DEFAULT_STATES",
    "DynamicPackRenderer",
    "import_codex_pack", "scan_codex_home",
    "generate_default_pet",
]
