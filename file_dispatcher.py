"""File Event Dispatcher — deduplicates events from Shell + Directory watchers.

Ensures the same file operation only triggers one animation, even if both
ShellWatcher and ReadDirectoryChangesW report it.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from file_event import FileSemanticEvent

LOGGER = logging.getLogger("pet.file_dispatcher")

# Deduplication window in seconds
DEDUPE_WINDOW_MS = 500


class FileEventDispatcher:
    """Deduplicates file events from multiple sources."""

    def __init__(self, callback: Callable[[FileSemanticEvent], None],
                 dedupe_ms: int = DEDUPE_WINDOW_MS):
        self._callback = callback
        self._dedupe_ms = dedupe_ms
        self._recent: dict[str, float] = {}  # dedupe_key -> timestamp

    def dispatch(self, event: FileSemanticEvent):
        """Dispatch an event, deduplicating within the time window."""
        key = self._dedupe_key(event)
        now = time.time()
        last = self._recent.get(key, 0)
        if now - last < self._dedupe_ms / 1000.0:
            LOGGER.debug("Deduplicated: %s", key)
            return
        self._recent[key] = now
        # Cleanup old entries
        cutoff = now - self._dedupe_ms / 1000.0 * 2
        self._recent = {k: v for k, v in self._recent.items() if v > cutoff}
        # Dispatch
        LOGGER.info("Dispatching: action=%s path=%s source=%s",
                     event.action, event.path, event.source)
        self._callback(event)

    def _dedupe_key(self, event: FileSemanticEvent) -> str:
        """Generate a deduplication key."""
        path_str = str(event.path) if event.path else "<unknown>"
        # Normalize path
        path_str = path_str.lower().replace("/", "\\")
        return f"{event.action}:{path_str}"
