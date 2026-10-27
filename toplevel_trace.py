"""Top-level window show tracer — popup-storm investigation aid.

install(app) logs every top-level widget Show to logs/toplevel_trace.log.
Cheap (one append per window show); safe to leave in production.
"""
from pathlib import Path

PENDING = []
_LOG = Path(__file__).resolve().parent / "logs" / "toplevel_trace.log"


def install(app):
    import sys
    import traceback
    from PyQt5.QtCore import QObject, QEvent

    class _Trace(QObject):
        captured = 0

        def eventFilter(self, obj, event):
            if event.type() == QEvent.Show and obj.isWidgetType() and obj.isWindow():
                _Trace.captured += 1
                try:
                    _LOG.parent.mkdir(exist_ok=True)
                    name = type(obj).__name__
                    wname = obj.objectName()
                    size = f"{obj.width()}x{obj.height()}"
                    flags = hex(int(obj.windowFlags()))
                    with open(_LOG, "a", encoding="utf-8") as fh:
                        fh.write(f"{name} name={wname!r} size={size} flags={flags}\n")
                        if _Trace.captured <= 3:
                            stack = "".join(traceback.format_stack(limit=12)[:-1])
                            fh.write(stack + "\n")
                except OSError:
                    pass
            return False

    PENDING.append(_Trace())
    app.installEventFilter(PENDING[-1])
