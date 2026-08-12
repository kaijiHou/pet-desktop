"""
Desktop Pet Window — PyQt5 floating transparent pet with animations.
"""

import math
import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QRect, QSize, pyqtSignal, QThread,
)
from PyQt5.QtGui import (
    QPainter, QPixmap, QImage, QFont, QColor, QPen, QBrush,
    QPainterPath, QFontMetrics, QCursor, QIcon, QTransform, QKeyEvent,
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QAction, QSystemTrayIcon,
    QInputDialog, QMessageBox, QDialog, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout, QSlider, QCheckBox,
    QSpinBox, QFormLayout, QGroupBox, QDialogButtonBox,
)

from config import Config, CONFIG_DIR
from pet_sprite import PetSpriteLoader, generate_sprite, SPRITE_W, SPRITE_H
from pocket_service import PocketService
from pocket_ui import PocketDialog
from file_watch import FileWatchService
from events import AnimationController, AppEvent, EventDispatcher
from reminder_service import ReminderService
from reminder_ui import AddReminderDialog, ReminderListDialog
import sounds


# ─── Settings Dialog ─────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Settings window for the pet."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("🐱 Mochi Settings")
        self.setFixedSize(380, 160)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Clippy is ready to keep your local reminders."))

        # ── Buttons ──
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        self.accept()


# ─── Pet Window ─────────────────────────────────────────────────────────────

class PetWindow(QWidget):
    """The main floating pet window."""

    STATE_IDLE = "idle"
    STATE_TALKING = "talking"
    STATE_ALERT = "alert"
    STATE_SLEEP = "sleep"

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.reminder = ReminderService()
        self.pocket = PocketService()
        self.file_watch = FileWatchService()
        self.events = EventDispatcher(self)
        self.animation_controller = AnimationController({"RestPose"})
        self.events.event_received.connect(self._handle_app_event)
        self.file_watch.on_change = lambda change: self.events.dispatch(
            AppEvent("windows", change.action, change)
        )

        # Sprite loader
        self.sprite_loader = PetSpriteLoader(CONFIG_DIR / "assets", config.get("pet_scale", 2))

        # State
        self._state = self.STATE_IDLE
        self._frame = 0
        self._drag_pos = QPoint()
        self._dragging = False
        self._last_screen_rect = None

        # Pet size (from actual sprite dimensions)
        self._pet_w = int(SPRITE_W * config.get("pet_scale", 3))
        self._pet_h = int(SPRITE_H * config.get("pet_scale", 3))

        # UI setup
        self._setup_window()
        self._setup_tray()
        self._setup_timers()
        self._setup_callbacks()
        self._setup_speech_bubble()

        # Position
        self._load_position()
        QApplication.instance().applicationStateChanged.connect(self._application_state_changed)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setAcceptDrops(True)
        self.setFixedSize(self._pet_w + 20, self._pet_h + 20)
        self.setMouseTracking(True)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Create a simple icon
        icon_pixmap = QPixmap(32, 32)
        icon_pixmap.fill(Qt.transparent)
        # Draw simple cat face
        painter = QPainter(icon_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(255, 200, 150)))
        painter.setPen(QPen(QColor(60, 40, 40), 1))
        painter.drawEllipse(4, 4, 24, 24)
        # Eyes
        painter.setBrush(QBrush(QColor(60, 60, 80)))
        painter.drawEllipse(10, 11, 5, 5)
        painter.drawEllipse(19, 11, 5, 5)
        painter.end()

        self.tray_icon.setIcon(QIcon(icon_pixmap))
        self.tray_icon.setToolTip(f"{self.config.pet_name} — Desktop Pet")

        # Tray menu
        tray_menu = QMenu()

        add_action = tray_menu.addAction("➕ Add Reminder")
        add_action.triggered.connect(self._open_add_reminder)
        reminder_action = tray_menu.addAction("⏰ My Reminders")
        reminder_action.triggered.connect(self._open_reminders)
        pocket_action = tray_menu.addAction("📥 Pocket")
        pocket_action.triggered.connect(self._open_pocket)

        tray_menu.addSeparator()

        settings_action = tray_menu.addAction("⚙️ Settings")
        settings_action.triggered.connect(self._open_settings)

        pet_action = tray_menu.addAction("😴 / 🙋 Pet State")
        pet_menu = QMenu("Change State", self)
        for state in [self.STATE_IDLE, self.STATE_TALKING, self.STATE_ALERT, self.STATE_SLEEP]:
            a = pet_menu.addAction(state.capitalize())
            a.triggered.connect(lambda checked, s=state: self.set_state(s))
        pet_action.setMenu(pet_menu)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("✖️ Keluar")
        quit_action.triggered.connect(self._quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.tray_icon.activated.connect(self._tray_activated)

    def _setup_timers(self):
        # Animation timer — uses per-frame durations from Clippy data
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.setSingleShot(True)  # each frame schedules next
        self._schedule_next_frame()

        # One-shot timer scheduled for the nearest pending reminder.
        self._remind_timer = QTimer(self)
        self._remind_timer.setSingleShot(True)
        self._remind_timer.timeout.connect(self._check_due_reminders)

        # Idle check: after 5 min no activity → sleep
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start(60000)  # every minute
        self._last_activity = time.time()

    def _schedule_next_frame(self):
        """Get the duration for current frame and schedule next tick."""
        dur = self.sprite_loader.get_duration(self._state, self._frame)
        # Clamp to reasonable range (16ms = 60fps, 2000ms = 0.5fps)
        self._anim_timer.start(max(16, min(2000, dur)))

    def _setup_callbacks(self):
        self.reminder.on_reminder_due = self._on_reminder_due
        self._schedule_next_reminder()

    def _setup_speech_bubble(self):
        """Speech bubble state — drawn inside PetWindow paintEvent."""
        self._bubble_text = ""
        self._bubble_display = ""
        self._bubble_char = 0
        self._bubble_visible = False
        self._bubble_dismiss_ms = 6000
        self._bubble_timer = QTimer(self)
        self._bubble_timer.timeout.connect(self._bubble_type)
        self._bubble_dismiss = QTimer(self)
        self._bubble_dismiss.timeout.connect(self._bubble_hide)
        self._bubble_dismiss.setSingleShot(True)

    def _bubble_type(self):
        if self._bubble_char < len(self._bubble_text):
            self._bubble_char += 1
            self._bubble_display = self._bubble_text[:self._bubble_char]
            self.update()
        else:
            self._bubble_timer.stop()

    def _bubble_hide(self):
        self._bubble_visible = False
        self._bubble_timer.stop()
        self._bubble_dismiss.stop()
        self.update()

    def show_bubble(self, text, auto_dismiss_ms=6000):
        self._bubble_text = text
        self._bubble_display = ""
        self._bubble_char = 0
        self._bubble_visible = True
        self._bubble_dismiss_ms = auto_dismiss_ms
        self._bubble_timer.start(30)
        if auto_dismiss_ms > 0:
            total_ms = min(len(text) * 30 + 2000, auto_dismiss_ms)
            self._bubble_dismiss.start(total_ms)
        self.update()

    def show_bubble_now(self, text, auto_dismiss_ms=5000):
        self._bubble_text = text
        self._bubble_display = text
        self._bubble_char = len(text)
        self._bubble_visible = True
        self._bubble_dismiss_ms = auto_dismiss_ms
        self._bubble_dismiss.stop()
        if auto_dismiss_ms > 0:
            self._bubble_dismiss.start(auto_dismiss_ms)
        self.update()

    def _draw_bubble(self, painter):
        """Draw speech bubble within the pet window."""
        if not self._bubble_visible or not self._bubble_display:
            return

        # Bubble dimensions (relative to PetWindow top)
        margin = 5
        max_bw = self.width() - margin * 2
        padding = 10
        tail_size = 8

        # Calculate text size
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(
            QRect(0, 0, max_bw - padding * 2, 200),
            Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
            self._bubble_display,
        )
        bw = min(max_bw, max(80, text_rect.width() + padding * 2 + 4))
        bh = min(140, text_rect.height() + padding * 2 + tail_size + 4)
        bx = (self.width() - bw) // 2
        by = margin

        # Bubble path
        path = QPainterPath()
        radius = 10
        path.addRoundedRect(bx, by, bw, bh - tail_size, radius, radius)
        # Tail pointing down
        tail_x = bx + bw // 2
        tail_y = by + bh - tail_size
        path.moveTo(tail_x - tail_size, tail_y)
        path.lineTo(tail_x, tail_y + tail_size)
        path.lineTo(tail_x + tail_size, tail_y)
        path.closeSubpath()

        # Fill + border
        painter.fillPath(path, QColor(255, 255, 255, 235))
        painter.setPen(QPen(QColor(100, 80, 80), 1.2))
        painter.drawPath(path)

        # Text
        painter.setPen(QColor(50, 40, 40))
        text_area = QRect(bx + padding, by + padding,
                          bw - padding * 2, bh - tail_size - padding * 2)
        painter.drawText(text_area, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                         self._bubble_display)

        # Typing cursor
        if self._bubble_char < len(self._bubble_text):
            import time
            if int(time.time() * 3) % 2:
                painter.drawText(text_area.right() - 5, text_area.bottom(), "▍")

    def _load_position(self):
        screen = QApplication.primaryScreen().geometry()
        x = self.config.get("pet_x", -1)
        y = self.config.get("pet_y", -1)
        if x < 0 or y < 0:
            # Default: bottom-right
            x = screen.width() - self.width() - 20
            y = screen.height() - self.height() - 60
        self.move(x, y)

    # ── Event Handlers ──

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # Generate sprite
            img = generate_sprite(self._state, self._frame, self.config.get("pet_scale", 3))
            qimage = self._pil_to_qimage(img)
            pixmap = QPixmap.fromImage(qimage)

            # Center in window (shift down to make room for bubble)
            bubble_offset = 0
            if self._bubble_visible:
                bubble_offset = 60
            x = (self.width() - pixmap.width()) // 2
            y = bubble_offset + (self.height() - pixmap.height() - bubble_offset) // 2
            painter.drawPixmap(x, y, pixmap)

            # Pet name label
            painter.setPen(QColor(100, 80, 80))
            painter.setFont(QFont("Segoe UI", 7))
            name = self.config.pet_name
            fm = QFontMetrics(painter.font())
            tw = fm.horizontalAdvance(name)
            painter.drawText((self.width() - tw) // 2, self.height() - 2, name)

            # Speech bubble overlay
            self._draw_bubble(painter)

            painter.end()
        except Exception as e:
            print(f"Paint error: {e}")
            import traceback
            traceback.print_exc()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._last_activity = time.time()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            self._last_activity = time.time()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            # Save position
            self.config.set("pet_x", self.x())
            self.config.set("pet_y", self.y())
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.show_bubble("Hai! 👋", 2500)
            self.set_state(self.STATE_TALKING)
            event.accept()

    def wheelEvent(self, event):
        # Scroll to adjust volume / scale? Let's do scale change
        delta = event.angleDelta().y()
        if delta > 0:
            self._change_scale(0.1)
        else:
            self._change_scale(-0.1)
        event.accept()

    def enterEvent(self, event):
        self._last_activity = time.time()
        if self._state == self.STATE_SLEEP:
            self.set_state(self.STATE_IDLE)

    def dragEnterEvent(self, event):
        if self._local_drop_paths(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = self._local_drop_paths(event)
        if not paths:
            event.ignore()
            return

        added = 0
        duplicates = 0
        for path in paths:
            before = len(self.pocket.list_items())
            try:
                self.pocket.add(path)
                if len(self.pocket.list_items()) == before:
                    duplicates += 1
                else:
                    added += 1
                    if path.is_dir():
                        self.file_watch.watch(path)
            except (OSError, ValueError):
                continue

        if added:
            self.events.dispatch(AppEvent("pocket", "receive", {"count": added}))
            detail = f" ({duplicates} already there)" if duplicates else ""
            self.show_bubble(f"📥 Added {added} item(s) to Pocket{detail}.", 4500)
            QTimer.singleShot(3000, lambda: self.set_state(self.STATE_IDLE))
        elif duplicates:
            self.show_bubble("✅ Already in Pocket.", 3000)
        else:
            self.show_bubble("⚠️ I couldn't add those items.", 3500)
        event.acceptProposedAction()

    @staticmethod
    def _local_drop_paths(event):
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        paths = []
        for url in mime.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.exists():
                    paths.append(path)
        return paths

    # ── Animation ──

    def _animate(self):
        self._frame += 1
        self.update()
        self._schedule_next_frame()

    def set_state(self, state: str):
        if state != self._state:
            self._state = state
            self._frame = 0
            self.update()

    def _check_idle(self):
        if self._state == self.STATE_SLEEP:
            return
        idle_time = time.time() - self._last_activity
        if idle_time > 300:  # 5 minutes
            self.set_state(self.STATE_SLEEP)
            self.show_bubble_now("😴 Zzz... aku tidur dulu ya, bangunin kalau perlu~", 4000)

    # ── Reminders ──

    def _schedule_next_reminder(self):
        self._remind_timer.stop()
        due_at = self.reminder.next_due_at()
        if due_at is None:
            return
        delay_ms = max(0, int((due_at - datetime.now()).total_seconds() * 1000))
        self._remind_timer.start(min(delay_ms, 2_147_000_000))

    def _check_due_reminders(self):
        self.reminder.check_due()
        self._schedule_next_reminder()

    def _application_state_changed(self, state):
        if state == Qt.ApplicationActive:
            self._check_due_reminders()

    def _on_reminder_due(self, reminder):
        self.events.dispatch(AppEvent("reminder", "due", reminder))
        sounds.play_reminder()
        self.show_bubble(f"⏰ Reminder: {reminder.content}", 10000)
        # Reset to idle after a bit
        QTimer.singleShot(3000, lambda: self.set_state(self.STATE_IDLE))

    def _handle_app_event(self, event):
        # The legacy renderer currently exposes only coarse states; Phase 16
        # loads the complete animation catalog before it becomes the main track.
        if event.category == "reminder":
            self.set_state(self.STATE_ALERT)
        elif event.category in {"pocket", "file_operation", "windows"}:
            self.set_state(self.STATE_TALKING)

    def _open_add_reminder(self):
        dialog = AddReminderDialog(self)
        if dialog.exec_():
            content, due_at = dialog.values()
            self.reminder.add_reminder(content, due_at)
            self._schedule_next_reminder()
            self.show_bubble(f"✅ Reminder saved for {due_at:%Y-%m-%d %H:%M}", 4000)

    def _open_reminders(self):
        ReminderListDialog(self.reminder, self).exec_()
        self._schedule_next_reminder()

    def _open_pocket(self):
        PocketDialog(self.pocket, self, event_dispatcher=self.events).exec_()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.show_bubble("Hai! 👋", 2500)
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click — toggle visibility
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()

    # ── Context Menu ──

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #fff8f0; border: 1px solid #d0c0b0; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #ecd8c0; }
        """)

        add_action = menu.addAction("➕ Add Reminder")
        reminder_action = menu.addAction("⏰ My Reminders")
        pocket_action = menu.addAction("📥 Pocket")
        menu.addSeparator()
        settings_action = menu.addAction("⚙️ Settings")
        menu.addSeparator()
        quit_action = menu.addAction("✖️ Keluar")

        action = menu.exec_(pos)
        if action == add_action:
            self._open_add_reminder()
        elif action == reminder_action:
            self._open_reminders()
        elif action == pocket_action:
            self._open_pocket()
        elif action == settings_action:
            self._open_settings()
        elif action == quit_action:
            self._quit_app()

    def _open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_():
            self._update_from_settings()

    def _update_from_settings(self):
        self.tray_icon.setToolTip(f"{self.config.pet_name} — Desktop Pet")

    # ── Utilities ──

    def _pil_to_qimage(self, pil_image):
        """Convert PIL Image to QImage manually (no ImageQt dependency)."""
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        from PyQt5.QtGui import QImage
        return QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)

    def _change_scale(self, delta):
        current = float(self.config.get("pet_scale", 3))
        new_scale = max(1.0, min(6.0, current + delta))
        new_scale = round(new_scale, 1)
        self.config.set("pet_scale", new_scale)
        self._pet_w = int(SPRITE_W * new_scale)
        self._pet_h = int(SPRITE_H * new_scale)
        self.setFixedSize(self._pet_w + 20, self._pet_h + 20)

    def _quit_app(self):
        self.file_watch.stop_all()
        self._bubble_hide()
        self.tray_icon.hide()
        QApplication.quit()


# ─── Main Entry ─────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Pet")
    app.setQuitOnLastWindowClosed(False)

    config = Config()

    window = PetWindow(config)
    window.show()

    # Welcome message
    name = config.pet_name
    welcome_msg = (
        f"Hai! Aku {name}~ 🐱\n"
        "Aku siap membantu mengingat hal pentingmu!"
    )

    QTimer.singleShot(1500, lambda: (
        window.show_bubble(welcome_msg, 8000),
        window.set_state(PetWindow.STATE_TALKING),
        QTimer.singleShot(2000, lambda: window.set_state(PetWindow.STATE_IDLE)),
    ))

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
