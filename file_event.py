"""File Semantic Event — unified event type for file operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import time


@dataclass
class FileSemanticEvent:
    """A file operation event with semantic meaning."""
    action: str  # created, deleted, dir_created, dir_removed, renamed, dir_renamed, directory_changed
    path: Optional[Path] = None
    is_dir: bool = False
    source: str = "shell"  # shell, directory_watch, explorer_watch, app
    timestamp: float = field(default_factory=time.time)

    @property
    def semantic(self) -> str:
        """Map action to PetWindow semantic animation."""
        mapping = {
            "created": "CREATE_FILE",
            "deleted": "DELETE_FILE",
            "dir_created": "CREATE_FILE",
            "dir_removed": "DELETE_FILE",
            "renamed": "RENAME_FILE",
            "dir_renamed": "RENAME_FILE",
            "directory_changed": "IDLE",
        }
        return mapping.get(self.action, "IDLE")

    @property
    def bubble_text(self) -> str:
        """Human-readable bubble text."""
        mapping = {
            "created": "检测到新建文件",
            "deleted": "检测到删除文件",
            "dir_created": "检测到新建文件夹",
            "dir_removed": "检测到删除文件夹",
            "renamed": "检测到文件重命名",
            "dir_renamed": "检测到文件夹重命名",
            "directory_changed": "",
        }
        return mapping.get(self.action, "检测到文件操作")
