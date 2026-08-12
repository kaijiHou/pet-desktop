"""Event-driven Windows directory watching via ReadDirectoryChangesW."""

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
from pathlib import Path
import struct
import threading


ACTION_NAMES = {1: "added", 2: "removed", 3: "modified", 4: "renamed_from", 5: "renamed_to"}


@dataclass(frozen=True)
class FileChangeEvent:
    directory: Path
    path: Path
    action: str


def parse_notifications(data: bytes, directory: Path):
    events = []
    offset = 0
    while offset + 12 <= len(data):
        next_offset, action, name_length = struct.unpack_from("<III", data, offset)
        name_start = offset + 12
        name = data[name_start:name_start + name_length].decode("utf-16-le", errors="replace")
        events.append(FileChangeEvent(directory, directory / name, ACTION_NAMES.get(action, "unknown")))
        if next_offset == 0:
            break
        offset += next_offset
    return events


class WindowsDirectoryBackend:
    FILTER = 0x00000001 | 0x00000002 | 0x00000004 | 0x00000008 | 0x00000010

    def __init__(self):
        self._handles = {}
        self._lock = threading.Lock()

    def watch(self, directory, stop_event):
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateFileW.restype = wintypes.HANDLE
        handle = kernel32.CreateFileW(
            str(directory), 0x0001, 0x00000001 | 0x00000002 | 0x00000004,
            None, 3, 0x02000000, None,
        )
        if handle == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), "CreateFileW failed")
        key = str(directory).casefold()
        with self._lock:
            self._handles[key] = handle
        buffer = ctypes.create_string_buffer(65536)
        returned = wintypes.DWORD()
        try:
            while not stop_event.is_set():
                ok = kernel32.ReadDirectoryChangesW(
                    handle, buffer, len(buffer), False, self.FILTER,
                    ctypes.byref(returned), None, None,
                )
                if not ok:
                    if stop_event.is_set():
                        break
                    raise OSError(ctypes.get_last_error(), "ReadDirectoryChangesW failed")
                yield bytes(buffer.raw[:returned.value])
        finally:
            with self._lock:
                self._handles.pop(key, None)
            kernel32.CloseHandle(handle)

    def cancel(self, directory):
        key = str(Path(directory).resolve()).casefold()
        with self._lock:
            handle = self._handles.get(key)
        if handle:
            ctypes.windll.kernel32.CancelIoEx(handle, None)


class FileWatchService:
    """Watch only explicitly supplied directories and dispatch factual events."""

    def __init__(self, backend=None):
        self.backend = backend or WindowsDirectoryBackend()
        self.on_change = None
        self._stops = {}
        self._threads = {}

    def watch(self, directory):
        path = Path(directory).resolve()
        if not path.is_dir():
            raise NotADirectoryError(path)
        key = str(path).casefold()
        if key in self._threads:
            return False
        stop_event = threading.Event()
        thread = threading.Thread(target=self._run, args=(path, stop_event), daemon=True)
        self._stops[key] = stop_event
        self._threads[key] = thread
        thread.start()
        return True

    def _run(self, directory, stop_event):
        try:
            for data in self.backend.watch(directory, stop_event):
                for event in parse_notifications(data, directory):
                    if self.on_change:
                        self.on_change(event)
        except OSError:
            return

    def watched_directories(self):
        return [Path(key) for key in self._threads]

    def stop_all(self):
        for key, stop in self._stops.items():
            stop.set()
            cancel = getattr(self.backend, "cancel", None)
            if cancel:
                cancel(Path(key))
        for thread in self._threads.values():
            thread.join(timeout=1)
        self._stops.clear()
        self._threads.clear()
