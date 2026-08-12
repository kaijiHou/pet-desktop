"""
Desktop Pet Window — WebEngine-based Clippy renderer.
Uses clippyjs via HTML5 Canvas for smooth pixel-perfect rendering.
"""

import json, math, sys, time, os, random
from datetime import datetime
from pathlib import Path

# CRITICAL: Must be set before ANY PyQt5 imports
import PyQt5.QtCore
PyQt5.QtCore.QCoreApplication.setAttribute(PyQt5.QtCore.Qt.AA_ShareOpenGLContexts, True)

from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QUrl
from PyQt5.QtGui import QFont, QColor, QPen, QFontMetrics, QPainter, QPixmap, QIcon, QPainterPath
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QAction, QSystemTrayIcon,
    QInputDialog, QMessageBox, QDialog, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout, QSlider, QCheckBox,
    QSpinBox, QFormLayout, QGroupBox, QDialogButtonBox,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView

from config import Config, CONFIG_DIR
from pocket_service import PocketService
from pocket_ui import PocketDialog
from file_watch import FileWatchService
from events import AnimationController, AppEvent, EventDispatcher
from reminder_service import ReminderService
from reminder_ui import AddReminderDialog, ReminderListDialog
import sounds


ASSETS_DIR = CONFIG_DIR / "assets"


# ─── Windows 95 / Office 97 Stylesheet ──────────────────────────────────────

WIN95_BG = "#C0C0C0"
WIN95_FONT = "MS Sans Serif"

WIN95_STYLESHEET = f"""
QDialog {{
    background-color: {WIN95_BG};
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
}}
QGroupBox {{
    background-color: {WIN95_BG};
    border: 2px solid;
    border-color: #FFFFFF #808080 #808080 #FFFFFF;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    background-color: {WIN95_BG};
    color: #000000;
}}
QLineEdit {{
    background-color: #FFFFFF;
    border: 2px solid;
    border-color: #808080 #FFFFFF #FFFFFF #808080;
    padding: 2px 4px;
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
    color: #000000;
}}
QSpinBox {{
    background-color: #FFFFFF;
    border: 2px solid;
    border-color: #808080 #FFFFFF #FFFFFF #808080;
    padding: 2px 4px;
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
    color: #000000;
}}
QSpinBox::up-button {{
    border: 1px solid #808080;
    background: {WIN95_BG};
}}
QSpinBox::down-button {{
    border: 1px solid #808080;
    background: {WIN95_BG};
}}
QCheckBox {{
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
    spacing: 6px;
    color: #000000;
}}
QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    background: #FFFFFF;
    border: 2px solid;
    border-color: #808080 #FFFFFF #FFFFFF #808080;
}}
QCheckBox::indicator:checked {{
    background: #FFFFFF;
}}
QPushButton {{
    background-color: {WIN95_BG};
    border: 2px solid;
    border-color: #FFFFFF #808080 #808080 #FFFFFF;
    padding: 4px 16px;
    min-width: 70px;
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
    color: #000000;
}}
QPushButton:pressed {{
    border-color: #808080 #FFFFFF #FFFFFF #808080;
    background-color: #A0A0A0;
}}
QDialogButtonBox QPushButton {{
    min-width: 75px;
}}
QLabel {{
    font-family: '{WIN95_FONT}';
    font-size: 11pt;
    color: #000000;
    background-color: {WIN95_BG};
}}
"""


# ─── Settings Dialog ─────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Clippy Settings")
        self.setMinimumSize(360, 180)
        self.resize(400, 200)
        self.setStyleSheet(WIN95_STYLESHEET)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Clippy is ready to keep your local reminders."))

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Bobo button
        bobo_layout = QHBoxLayout()
        bobo_layout.addStretch()
        self.bobo_btn = QPushButton("😴 Suruh Clippy Bobo")
        self.bobo_btn.clicked.connect(self._bobo)
        bobo_layout.addWidget(self.bobo_btn)
        bobo_layout.addStretch()
        layout.addLayout(bobo_layout)
        self._going_bobo = False

    def _bobo(self):
        self._going_bobo = True
        self.accept()

    def _save(self):
        self.accept()


# ─── PetWindow (WebEngine) ──────────────────────────────────────────────────

class PetWindow(QWidget):
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
        animation_names = json.loads((Path(__file__).parent / "assets" / "animations.json").read_text(encoding="utf-8"))
        self.events = EventDispatcher(self)
        self.animation_controller = AnimationController(animation_names)
        self.events.event_received.connect(self._handle_app_event)
        self.file_watch.on_change = lambda change: self.events.dispatch(
            AppEvent("windows", change.action, change)
        )
        self._state = self.STATE_IDLE
        self._drag_pos = QPoint()
        self._dragging = False
        self._scale_val = config.get("pet_scale", 3)

        self._setup_window()
        self._setup_webview()
        self._setup_tray()
        self._setup_timers()
        self._setup_callbacks()
        self._setup_speech_bubble()
        self._load_position()
        QApplication.instance().applicationStateChanged.connect(self._application_state_changed)

    def _setup_window(self):
        w = 124 * self._scale_val + 20
        h = 93 * self._scale_val + 20
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setAcceptDrops(True)
        self.setFixedSize(int(w), int(h))
        self.setMouseTracking(True)

    def _setup_webview(self):
        self.web = QWebEngineView(self)
        self.web.setAttribute(Qt.WA_TranslucentBackground)
        self.web.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.web.page().setBackgroundColor(Qt.transparent)
        margin = 10
        self.web.setGeometry(int(margin), int(margin), int(124 * self._scale_val), int(93 * self._scale_val))
        self.web.show()

        # Load the HTML page
        html_path = str(ASSETS_DIR / "clippy.html")
        qurl = QUrl.fromLocalFile(html_path)
        self.web.load(qurl)
        self.web.page().loadFinished.connect(self._on_page_loaded)

    def _on_page_loaded(self, ok):
        if ok:
            self.web.page().runJavaScript(f"setScale({self._scale_val});")
            self.web.page().runJavaScript("setAnimation('idle');")
            sounds.play_startup()
            # Delay welcome message until page is ready.
            name = self.config.pet_name
            msg = f"Hai! Aku {name}~ 📎\nAku siap membantu mengingat hal pentingmu."
            QTimer.singleShot(500, lambda: (
                self.show_bubble(msg, 12000),
                self.set_state(PetWindow.STATE_TALKING),
            ))

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(200, 200, 210))
        p.setPen(QPen(QColor(100, 100, 120), 1))
        p.drawRoundedRect(4, 4, 24, 24, 6, 6)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(10, 10, 5, 5)
        p.drawEllipse(19, 10, 5, 5)
        p.setBrush(QColor(40, 40, 50))
        p.drawEllipse(12, 12, 3, 3)
        p.drawEllipse(21, 12, 3, 3)
        p.end()
        self.tray_icon.setIcon(QIcon(pix))
        self.tray_icon.setToolTip("Clippy — Desktop Pet")
        tray_menu = QMenu()

        a = tray_menu.addAction("➕ Add Reminder")
        a.triggered.connect(self._open_add_reminder)
        a = tray_menu.addAction("⏰ My Reminders")
        a.triggered.connect(self._open_reminders)
        a = tray_menu.addAction("📥 Pocket")
        a.triggered.connect(self._open_pocket)
        tray_menu.addSeparator()
        a = tray_menu.addAction("⚙️ Settings")
        a.triggered.connect(self._open_settings)
        tray_menu.addSeparator()
        a = tray_menu.addAction("✖️ Keluar")
        a.triggered.connect(self._quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self._tray_activated)

    def _setup_timers(self):
        self._remind_timer = QTimer(self)
        self._remind_timer.setSingleShot(True)
        self._remind_timer.timeout.connect(self._check_due_reminders)
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start(60000)
        self._idle_variety_timer = QTimer(self)
        self._idle_variety_timer.timeout.connect(self._idle_variety)
        self._idle_variety_timer.start(random.randint(8000, 15000))
        self._last_activity = time.time()

    def _setup_callbacks(self):
        self.reminder.on_reminder_due = self._on_reminder_due
        self._schedule_next_reminder()

    def _setup_speech_bubble(self):
        """Speech bubble as a SEPARATE window (like Office 97 tooltip)."""
        self._bubble_text = ""
        self._bubble_display = ""
        self._bubble_char = 0
        self._bubble_visible = False
        self._bubble_timer = QTimer(self)
        self._bubble_timer.timeout.connect(self._bubble_type)
        self._bubble_dismiss = QTimer(self)
        self._bubble_dismiss.timeout.connect(self._bubble_hide)
        self._bubble_dismiss.setSingleShot(True)
        self._bubble_widget = None  # will create on demand

    def _ensure_bubble_widget(self):
        """Create the bubble as a child of PetWindow."""
        if self._bubble_widget is None:
            from PyQt5.QtWidgets import QLabel
            self._bubble_widget = QLabel(self)
            self._bubble_widget.setStyleSheet("background:transparent;border:none;")
            self._bubble_widget.hide()
        return self._bubble_widget

    def _bubble_type(self):
        if self._bubble_char < len(self._bubble_text):
            self._bubble_char += 1
            self._bubble_display = self._bubble_text[:self._bubble_char]
            self._update_bubble()
        else:
            self._bubble_timer.stop()

    def _bubble_hide(self):
        self._bubble_visible = False
        self._bubble_timer.stop()
        self._bubble_dismiss.stop()
        if self._bubble_widget:
            self._bubble_widget.hide()

    def _ensure_bubble_widget(self):
        """Create a separate tooltip window ABOVE PetWindow."""
        if self._bubble_widget is None:
            self._bubble_widget = QLabel(None)
            self._bubble_widget.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            )
            self._bubble_widget.setAttribute(Qt.WA_ShowWithoutActivating)
            self._bubble_widget.setStyleSheet("background:transparent;")
            self._bubble_widget.hide()
        return self._bubble_widget

    def _update_bubble(self):
        """Draw bubble above or below the PetWindow."""
        if not self._bubble_visible:
            return
        text = self._bubble_display if self._bubble_display else " "
        bw = self._ensure_bubble_widget()

        padding = 12
        font = QFont("MS Sans Serif", 8)
        fm = QFontMetrics(font)
        max_w = 260
        tr = fm.boundingRect(0, 0, max_w, 200,
                             Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text)
        bw_w = min(max_w, max(80, tr.width() + padding*2 + 8)) + 4
        bw_h = tr.height() + padding*2 + 16

        clippy_rect = self.geometry()
        screen = QApplication.primaryScreen().geometry()
        bx = clippy_rect.center().x() - bw_w // 2
        by = clippy_rect.top() - bw_h - 6
        bx = max(4, min(bx, screen.width() - bw_w - 4))
        if by < 4:
            by = clippy_rect.bottom() + 6

        bw.setGeometry(bx, by, bw_w, bw_h)
        bw.setFixedSize(bw_w, bw_h)

        pix = QPixmap(bw_w, bw_h)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        p.setPen(QPen(QColor(255, 255, 255), 1))
        p.drawLine(0, bw_h-1, 0, 0)
        p.drawLine(0, 0, bw_w, 0)
        p.setPen(QPen(QColor(128, 128, 128), 1))
        p.drawLine(0, bw_h-1, bw_w, bw_h-1)
        p.drawLine(bw_w-1, 0, bw_w-1, bw_h-1)
        p.fillRect(2, 2, bw_w-4, bw_h-4, QColor(255, 255, 225))

        p.setPen(QColor(0, 0, 0))
        p.setFont(font)
        p.drawText(QRect(padding, padding, bw_w-padding*2-2, bw_h-padding*2-2),
                   Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text)

        if self._bubble_char < len(self._bubble_text):
            if int(time.time()*3) % 2:
                p.drawText(bw_w-padding-8, bw_h-padding, "▍")
        p.end()

        bw.setPixmap(pix)
        bw.show()
        bw.raise_()

    def show_bubble(self, text, auto_dismiss_ms=6000):
        self._bubble_text = text
        self._bubble_display = ""
        self._bubble_char = 0
        self._bubble_visible = True
        self._bubble_timer.start(20)  # faster typing
        if auto_dismiss_ms > 0:
            total = max(auto_dismiss_ms, len(text) * 20 + 3000)
            self._bubble_dismiss.start(total)
        self._update_bubble()

    def show_bubble_now(self, text, auto_dismiss_ms=5000):
        self._bubble_text = text
        self._bubble_display = text
        self._bubble_char = len(text)
        self._bubble_visible = True
        self._bubble_dismiss.stop()
        if auto_dismiss_ms > 0:
            self._bubble_dismiss.start(auto_dismiss_ms)
        self._update_bubble()

    def _load_position(self):
        screen = QApplication.primaryScreen().geometry()
        x, y = self.config.get("pet_x", -1), self.config.get("pet_y", -1)
        if x < 0 or y < 0:
            x, y = screen.width()-self.width()-20, screen.height()-self.height()-80
        self.move(x, y)

    def _js(self, code):
        """Run JavaScript in the web view."""
        self.web.page().runJavaScript(code)

    # ── Animation Contexts ──

    # Map behaviors to appropriate Clippy animations
    ANIM_IDLE = ['Idle1_1', 'IdleAtom', 'IdleSideToSide', 'RestPose',
                 'IdleFingerTap', 'IdleRopePile', 'IdleEyeBrowRaise']
    ANIM_TALKING = ['Explain', 'Alert', 'Processing', 'Thinking']
    ANIM_ALERT = ['Alert', 'GetAttention']
    ANIM_SLEEP = ['IdleSnooze']
    ANIM_THINKING = ['Thinking', 'IdleHeadScratch']
    ANIM_SEARCHING = ['Searching', 'CheckingSomething']
    ANIM_WAVE = ['Wave', 'Greeting']
    ANIM_LOOK = ['LookLeft', 'LookRight', 'LookUp', 'LookDown']
    ANIM_LOOK_AROUND = ['LookLeft', 'LookRight', 'LookLeft', 'LookRight', 'LookUp', 'LookDown']
    ANIM_WRITING = ['Writing', 'Print', 'Save']
    ANIM_HIDE = ['Hide']
    ANIM_CONGRATULATE = ['Congratulate', 'GetArtsy']
    ANIM_RECEIVE = ['Save']

    def _random_anim(self, group):
        """Pick a random animation from a group."""
        import random
        idx = random.randint(0, len(group) - 1)
        return group[idx]

    def set_state(self, state, anim_group=None):
        """Set state and optionally specify which animation group to use."""
        self._state = state
        if anim_group:
            anim = self._random_anim(anim_group)
        elif state == self.STATE_IDLE:
            anim = self._random_anim(self.ANIM_IDLE)
        elif state == self.STATE_TALKING:
            anim = self._random_anim(self.ANIM_TALKING)
        elif state == self.STATE_ALERT:
            anim = self._random_anim(self.ANIM_ALERT)
        elif state == self.STATE_SLEEP:
            anim = self._random_anim(self.ANIM_SLEEP)
        else:
            anim = self._random_anim(self.ANIM_IDLE)
        self._js(f"setAnimation('{anim}');")

    def play_look(self):
        """Play a random looking animation."""
        self.set_state(self.STATE_IDLE, self.ANIM_LOOK_AROUND)

    def play_wave(self):
        """Play waving animation."""
        self._state = self.STATE_TALKING
        self._js(f"setAnimation('{self._random_anim(self.ANIM_WAVE)}');")

    def play_writing(self):
        """Play writing/typing animation."""
        self._state = self.STATE_TALKING
        self._js(f"setAnimation('{self._random_anim(self.ANIM_WRITING)}');")

    def play_thinking(self):
        """Play thinking animation."""
        self._state = self.STATE_TALKING
        self._js(f"setAnimation('{self._random_anim(self.ANIM_THINKING)}');")

    def play_searching(self):
        """Play searching animation."""
        self._state = self.STATE_TALKING
        self._js(f"setAnimation('{self._random_anim(self.ANIM_SEARCHING)}');")

    def play_congratulate(self):
        """Play celebration animation."""
        self._state = self.STATE_TALKING
        self._js(f"setAnimation('{self._random_anim(self.ANIM_CONGRATULATE)}');")

    def _periodic_idle(self):
        """Occasionally play a different idle animation for variety."""
        if self._state == self.STATE_IDLE or self._state == self.STATE_SLEEP:
            return
        self._state = self.STATE_IDLE
        self.set_state(self.STATE_IDLE)
        self._last_activity = time.time()

    def _idle_variety(self):
        """Switch idle animations periodically to look alive."""
        if self._state == self.STATE_SLEEP:
            return
        if self._state != self.STATE_IDLE:
            return
        # Only change if it's been a while since last activity
        if time.time() - self._last_activity > 20:
            self.set_state(self.STATE_IDLE)  # picks a new random idle anim
            self._idle_variety_timer.start(random.randint(8000, 15000))

    # ── Events ──

    def paintEvent(self, event):
        # Bubble is now a separate window (no drawing needed here)
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._last_activity = time.time()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.config.set("pet_x", self.x())
            self.config.set("pet_y", self.y())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_wave()
            self.show_bubble("Hai! 👋", 2500)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self._scale_val = max(1, min(6, self._scale_val + (0.5 if delta > 0 else -0.5)))
        self.config.set("pet_scale", self._scale_val)
        w, h = 124 * self._scale_val + 20, 93 * self._scale_val + 20
        self.setFixedSize(int(w), int(h))
        self.web.setGeometry(10, 10, 124 * self._scale_val, 93 * self._scale_val)
        self._js(f"setScale({self._scale_val});")

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
        QTimer.singleShot(3000, lambda: self.set_state(self.STATE_IDLE))

    def _handle_app_event(self, event):
        animation = self.animation_controller.resolve(event)
        if animation:
            self._state = self.STATE_ALERT if event.category == "reminder" else self.STATE_TALKING
            self._js(f"setAnimation('{animation}');")

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

    def _check_idle(self):
        if self._state == self.STATE_SLEEP:
            return
        if time.time() - self._last_activity > 30:
            self.set_state(self.STATE_SLEEP)
            self.show_bubble_now("💤 Zzz... aku tidur dulu ya~", 4000)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.play_wave()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()

    # ── Context Menu ──

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu{background:#fff8f0;border:1px solid #d0c0b0;border-radius:6px;padding:4px;}QMenu::item{padding:6px 20px;border-radius:4px;}QMenu::item:selected{background:#ecd8c0;}")
        add_a = menu.addAction("➕ Add Reminder")
        list_a = menu.addAction("⏰ My Reminders")
        pocket_a = menu.addAction("📥 Pocket")
        menu.addSeparator()
        set_a = menu.addAction("⚙️ Settings")
        menu.addSeparator()
        quit_a = menu.addAction("✖️ Keluar")
        action = menu.exec_(pos)
        if action == add_a: self._open_add_reminder()
        elif action == list_a: self._open_reminders()
        elif action == pocket_a: self._open_pocket()
        elif action == set_a: self._open_settings()
        elif action == quit_a: self._quit_app()

    def _open_settings(self):
        d = SettingsDialog(self.config, self)
        if d.exec_():
            if d._going_bobo:
                self._go_bobo()
                return

    def _go_bobo(self):
        """Put Clippy to sleep."""
        self._js("setAnimation('GoodBye');")
        self.show_bubble("bye, aku bobo dulu. kalau butuh aku, bangunin aja yah", 5000)
        QTimer.singleShot(4000, self.hide)

    def _quit_app(self):
        self.file_watch.stop_all()
        self._bubble_hide()
        self.tray_icon.hide()
        QApplication.quit()


# ─── Main Entry ─────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Clippy Desktop Pet")
    app.setQuitOnLastWindowClosed(False)
    config = Config()

    window = PetWindow(config)
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
