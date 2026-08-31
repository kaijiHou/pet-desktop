"""
Desktop Pet Window — V2.2: unified theme, single-image character, Chinese UI.
"""
import math, random, sys, time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize, pyqtSignal, QThread, QUrl
from PyQt5.QtGui import (QPainter, QPixmap, QImage, QFont, QColor, QPen, QBrush,
    QPainterPath, QFontMetrics, QCursor, QIcon, QTransform)
from PyQt5.QtWidgets import (QApplication, QWidget, QMenu, QAction, QSystemTrayIcon,
    QInputDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QSlider, QCheckBox, QSpinBox, QFormLayout, QGroupBox, QDialogButtonBox)
from config import Config
from character import CharacterController, STEP_MS
from pet_sprite import ANIMATIONS, ASSETS_DIR, PetSpriteLoader, SPRITE_W, SPRITE_H
from pocket_service import PocketService
from pocket_ui import PocketDialog
from file_watch import FileWatchService
from events import AnimationController, AppEvent, EventDispatcher
from reminder_service import ReminderService
from reminder_ui import AddReminderDialog, ReminderListDialog
from wage.service import WageService
from wage.model import WORKDAY, ADJUSTED_WORKDAY, REST, LEAVE
from bubble_window import BubbleWindow
import sounds, theme


drop_log = logging.getLogger("pet.dnd")


class SettingsDialog(QDialog):
    """V2.2 settings with working-copy semantics + live size preview.

    Cancel restores the size the pet had before the dialog opened.
    """

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._work = dict(config.data)
        self._original_scale = float(config.get("pet_scale", 3))
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        # ── 角色 ──
        box = QGroupBox("角色"); form = QVBoxLayout(box)
        row_img = QHBoxLayout()
        self.image_label = QLabel(); self.image_label.setFixedSize(64, 64)
        self.image_label.setAlignment(Qt.AlignCenter); row_img.addWidget(self.image_label)
        col_btn = QVBoxLayout()
        self.import_button = QPushButton("选择图片...")
        self.reset_button = QPushButton("恢复默认角色")
        col_btn.addWidget(self.import_button); col_btn.addWidget(self.reset_button)
        col_btn.addStretch(); row_img.addLayout(col_btn); row_img.addStretch()
        form.addLayout(row_img)
        row_scale = QHBoxLayout(); row_scale.addWidget(QLabel("大小"))
        # slider 50%..200% (100% = default scale 3.0)
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(int(self._original_scale / 3.0 * 100))
        self.scale_slider.setTickPosition(QSlider.TicksBelow)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        row_scale.addWidget(self.scale_slider, 1)
        self.scale_pct_label = QLabel(f"{self.scale_slider.value()}%")
        self.scale_pct_label.setFixedWidth(48)
        row_scale.addWidget(self.scale_pct_label)
        form.addLayout(row_scale)
        self.name_check = QCheckBox("显示角色名称")
        self.name_check.setChecked(self._work.get("show_pet_name", False))
        form.addWidget(self.name_check); layout.addWidget(box)

        # ── 行为 ──
        box2 = QGroupBox("行为"); bl = QVBoxLayout(box2)
        self.top_check = QCheckBox("始终置顶")
        self.top_check.setChecked(self._work.get("always_on_top", True))
        self.wheel_check = QCheckBox("允许滚轮调整角色大小")
        self.wheel_check.setChecked(self._work.get("wheel_zoom_enabled", True))
        self.anim_check = QCheckBox("文件操作时播放动画")
        self.anim_check.setChecked(self._work.get("file_event_animations_enabled", True))
        self.badge_check = QCheckBox("口袋数量角标")
        self.badge_check.setChecked(self._work.get("pocket_badge_enabled", True))
        for w in (self.top_check, self.wheel_check, self.anim_check, self.badge_check):
            bl.addWidget(w)
        layout.addWidget(box2)

        # ── 提醒 ──
        box3 = QGroupBox("提醒"); rl = QVBoxLayout(box3)
        self.sound_check = QCheckBox("提醒声音")
        self.sound_check.setChecked(self._work.get("reminder_sound_enabled", True))
        self.bubble_check = QCheckBox("桌宠气泡")
        self.bubble_check.setChecked(self._work.get("reminder_bubble_enabled", True))
        rl.addWidget(self.sound_check); rl.addWidget(self.bubble_check); layout.addWidget(box3)

        # ── 数据 ──
        box4 = QGroupBox("数据"); dl = QHBoxLayout(box4)
        self.open_data_button = QPushButton("打开数据目录")
        self.open_data_button.clicked.connect(self._open_data_dir)
        self.open_log_button = QPushButton("打开日志目录")
        self.open_log_button.clicked.connect(self._open_log_dir)
        self.wage_button = QPushButton("工资与工时")
        self.wage_button.clicked.connect(lambda: self.parent()._open_wage_settings() if self.parent() else None)
        dl.addWidget(self.open_data_button); dl.addWidget(self.open_log_button); dl.addWidget(self.wage_button); dl.addStretch()
        layout.addWidget(box4)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save); buttons.rejected.connect(self._reject)
        layout.addWidget(buttons)
        self.import_button.clicked.connect(self._import_image)
        self.reset_button.clicked.connect(self._reset_image)
        self._refresh_preview()

    def _slider_to_scale(self, pct):
        return max(1.5, min(6.0, pct / 100.0 * 3.0))

    def _on_scale_changed(self, value):
        self.scale_pct_label.setText(f"{value}%")
        scale = self._slider_to_scale(value)
        self._work["pet_scale"] = scale
        if self.parent() and hasattr(self.parent(), "_update_scale_preview"):
            self.parent()._update_scale_preview(scale)

    def _refresh_preview(self):
        from character import draw_default_buddy
        from paths import PROJECT_ROOT
        name = self._work.get("character_image", ""); img = None
        if name:
            path = PROJECT_ROOT / "assets" / name
            if path.exists():
                try:
                    from PIL import Image as PILImage
                    img = PILImage.open(path).convert("RGBA")
                except OSError:
                    img = None
        if img is None:
            img = draw_default_buddy()
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
        self.image_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _import_image(self):
        from character import import_character_image
        from paths import PROJECT_ROOT
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择角色图片", "", "图片 (*.png *.webp)")
        if not path:
            return
        try:
            name = import_character_image(Path(path), PROJECT_ROOT / "assets")
        except ValueError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        self._work["character_image"] = name
        self._work["character_mode"] = "single"
        self._refresh_preview()
        if self.parent() and hasattr(self.parent(), "_reload_character_preview"):
            self.parent()._reload_character_preview()

    def _reset_image(self):
        self._work["character_image"] = ""
        self._refresh_preview()
        if self.parent() and hasattr(self.parent(), "_reload_character_preview"):
            self.parent()._reload_character_preview()

    def _open_data_dir(self):
        from paths import DATA_DIR
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))

    def _open_log_dir(self):
        from paths import LOG_DIR
        from PyQt5.QtGui import QDesktopServices
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR)))

    def _reject(self):
        # restore the pet's size as it was before the dialog opened
        if self.parent() and hasattr(self.parent(), "_update_scale_preview"):
            self.parent()._update_scale_preview(self._original_scale)
            self.parent().character.reload()
        self.reject()

    def _save(self):
        c = self.config
        c.set("pet_scale", self._slider_to_scale(self.scale_slider.value()))
        c.set("show_pet_name", self.name_check.isChecked())
        c.set("always_on_top", self.top_check.isChecked())
        c.set("wheel_zoom_enabled", self.wheel_check.isChecked())
        c.set("file_event_animations_enabled", self.anim_check.isChecked())
        c.set("pocket_badge_enabled", self.badge_check.isChecked())
        c.set("reminder_sound_enabled", self.sound_check.isChecked())
        c.set("reminder_bubble_enabled", self.bubble_check.isChecked())
        if "character_image" in self._work:
            c.set("character_image", self._work["character_image"])
            c.set("character_mode", self._work.get("character_mode", "single"))
        self.accept()


class PetWindow(QWidget):
    STATE_IDLE = "idle"
    STATE_TALKING = "talking"
    STATE_ALERT = "alert"
    STATE_SLEEP = "sleep"
    _SHEET_MAP = {"REMINDER": "Alert", "RECEIVE_FILE": "Save", "GIVE_FILE": "SendMail",
                  "DELETE_FILE": "EmptyTrash", "CREATE_FILE": "Show",
                  "RENAME_FILE": "Searching", "COPY_FILE": "Print", "MOVE_FILE": "SendMail",
                  "SUCCESS": "Save", "ERROR": "GetAttention"}

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.reminder = ReminderService()
        self.wage = WageService()
        self.wage.on_progress = self._on_wage_progress
        self.pocket = PocketService()
        self.file_watch = FileWatchService()
        self.events = EventDispatcher(self)
        self.animation_controller = AnimationController(set(AnimationController.MAPPING.values()) - {None})
        self.events.event_received.connect(self._handle_app_event)
        self.file_watch.on_change = lambda c: self.events.dispatch(AppEvent("windows", c.action, c))
        self.character = CharacterController(config, scale=config.get("pet_scale", 3))
        self.sprite_loader = PetSpriteLoader(scale=config.get("pet_scale", 3)) \
            if config.get("character_mode", "single") == "sheet" else None
        from shell_watcher import ShellWatcher
        self._shell_watcher = ShellWatcher()
        self._shell_watcher.start(self._on_shell_event)

        self._state = self.STATE_IDLE
        self._animation = "RestPose"
        self._frame = 0
        self._drag_pos = QPoint()
        self._dragging = False
        self._pressing = False
        self._press_pos = QPoint()
        self._moved = False
        self._drag_hover = False
        self._sem_steps = []
        self._sem_idx = -1
        self._sem_active = False
        self._sem_timer = QTimer(self)
        self._sem_timer.setSingleShot(True)
        self._sem_timer.timeout.connect(self._sem_tick)
        w, h = self.character.base_size()
        self._pet_w, self._pet_h = w, h
        self._quick_panel = None
        self._pocket_window = None
        self._today_wage = None
        self._setup_window()
        self._setup_tray()
        self._setup_timers()
        self._setup_callbacks()
        self._setup_speech_bubble()
        self._wage_last_overtime = False
        if self.wage.configured:
            missing = self.wage.missing_clockout_yesterday()
            if missing:
                self.show_bubble("昨天没有记录下班时间", 5000)
                QTimer.singleShot(1200, lambda: self._prompt_missing_clockout(missing))
        self._load_position()
        QApplication.instance().applicationStateChanged.connect(self._application_state_changed)

    def _setup_window(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        # Keep the otherwise transparent tool window targetable by Windows
        # accessibility/automation and recognizable in the task switcher.
        self.setWindowTitle("Desktop Pet")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setAcceptDrops(True)
        self.setFixedSize(self._pet_w + 40, self._pet_h + 60)
        self.setMouseTracking(True)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        from paths import PROJECT_ROOT
        icon_path = PROJECT_ROOT / "assets" / "app.ico"
        self.tray_icon.setIcon(QIcon(str(icon_path)) if icon_path.exists() else QIcon(self._draw_tray_icon()))
        self.tray_icon.setToolTip(f"{self.config.pet_name} — 桌面助手")
        m = QMenu()
        m.addAction("显示/隐藏角色").triggered.connect(self._toggle_visibility)
        m.addAction("今日收入").triggered.connect(self._open_today_wage)
        m.addAction("工时日历").triggered.connect(self._open_calendar)
        m.addSeparator()
        m.addAction("文件口袋").triggered.connect(self._open_pocket)
        m.addAction("新建提醒").triggered.connect(self._open_add_reminder)
        m.addAction("我的提醒").triggered.connect(self._open_reminders)
        m.addSeparator()
        m.addAction("设置").triggered.connect(self._open_settings)
        m.addSeparator()
        m.addAction("退出").triggered.connect(self._quit_app)
        self.tray_icon.setContextMenu(m)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self._tray_activated)

    @staticmethod
    def _draw_tray_icon():
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(100, 100, 120), 1.5))
        p.setBrush(QBrush(QColor(200, 210, 230)))
        p.drawRoundedRect(5, 10, 22, 18, 3, 3)
        p.drawArc(10, 2, 12, 16, 0, -180 * 16)
        p.end()
        return pix

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def _setup_timers(self):
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.setSingleShot(True)
        self._idle_variety_timer = QTimer(self)
        self._idle_variety_timer.timeout.connect(self._play_idle_variety)
        self._idle_variety_timer.setSingleShot(True)
        if (self.config.get("character_mode", "single") == "sheet"
                and self.config.get("idle_animations_enabled", False)):
            self._schedule_next_frame()
            self._schedule_idle_variety()
        self._remind_timer = QTimer(self)
        self._remind_timer.setSingleShot(True)
        self._remind_timer.timeout.connect(self._check_due_reminders)
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start(60000)
        self._last_activity = time.time()
        self._wage_timer = QTimer(self)
        self._wage_timer.setSingleShot(True)
        self._wage_timer.timeout.connect(self._on_wage_wake)
        self._schedule_next_wage_wake()

    def _schedule_next_frame(self):
        dur = self.sprite_loader.get_duration(self._animation, self._frame)
        self._anim_timer.start(max(16, min(2000, dur)))

    def _setup_callbacks(self):
        self.reminder.on_reminder_due = self._on_reminder_due
        self._schedule_next_reminder()

    def _setup_speech_bubble(self):
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
        # Qt's offscreen backend cannot safely composite repeated top-level
        # translucent windows; production Windows uses the external window,
        # tests retain the same state machine without creating native chrome.
        self._use_external_bubble = QApplication.platformName() != "offscreen"
        self._bubble_window = BubbleWindow(self)

    def _bubble_type(self):
        self._bubble_char = len(self._bubble_text)
        self._bubble_display = self._bubble_text
        self._bubble_timer.stop()
        self.update()

    def _bubble_hide(self):
        self._bubble_visible = False
        self._bubble_timer.stop()
        self._bubble_dismiss.stop()
        if self._use_external_bubble and self._bubble_window is not None:
            self._bubble_window.hide()
        self.update()

    def visible_pet_rect(self):
        """Return the current visible character bounds in this widget."""
        w, h = self.character.base_size()
        sf, dx, dy, rot = self._current_transform()
        cx = self.width() / 2 + dx
        cy = 20 + h / 2 + dy
        bbox = self.character.visible_alpha_bbox
        if self.character.mode != "single" or not bbox:
            return QRect(round(cx - w * sf / 2), round(cy - h * sf / 2),
                         max(1, round(w * sf)), max(1, round(h * sf)))
        image = self.character.get_single_frame()
        iw, ih = image.size
        left, top, right, bottom = bbox
        x1 = cx + (left / iw - 0.5) * w * sf
        x2 = cx + (right / iw - 0.5) * w * sf
        y1 = cy + (top / ih - 0.5) * h * sf
        y2 = cy + (bottom / ih - 0.5) * h * sf
        # Rotations are small semantic tilts; use a conservative bounding box.
        if rot:
            pad = abs(math.sin(math.radians(rot))) * max(x2 - x1, y2 - y1) * 0.12
            x1 -= pad; x2 += pad; y1 -= pad; y2 += pad
        return QRect(round(x1), round(y1), max(1, round(x2 - x1)), max(1, round(y2 - y1)))

    def visible_pet_global_rect(self):
        local = self.visible_pet_rect()
        return QRect(self.mapToGlobal(local.topLeft()), local.size())

    def _position_bubble(self):
        if self._bubble_visible and self._bubble_display and self._bubble_window is not None:
            screen = QApplication.screenAt(self.visible_pet_global_rect().center()) or QApplication.primaryScreen()
            self._bubble_window.place_near(self.visible_pet_global_rect(), screen)

    def show_bubble(self, text, auto_dismiss_ms=6000):
        self._bubble_text = text
        self._bubble_display = text
        self._bubble_char = len(text)
        self._bubble_visible = True
        self._bubble_dismiss_ms = auto_dismiss_ms
        if auto_dismiss_ms > 0:
            self._bubble_dismiss.start(auto_dismiss_ms)
        if self._bubble_window is not None:
            self._bubble_window.set_text(text)
            self._position_bubble()
            if self._use_external_bubble:
                self._bubble_window.show()
                self._bubble_window.raise_()
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
        if self._bubble_window is not None:
            self._bubble_window.set_text(text)
            self._position_bubble()
            if self._use_external_bubble:
                self._bubble_window.show()
                self._bubble_window.raise_()
        self.update()

    def _draw_bubble(self, painter):
        # Kept as a compatibility hook for old tests/themes.  Bubbles now
        # live in BubbleWindow so they can flip at screen edges and escape the
        # transparent PetWindow rectangle.
        return
        margin = 5; max_bw = self.width() - margin * 2; padding = 10; tail_size = 8
        font = QFont("Microsoft YaHei UI", 8)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(QRect(0, 0, max_bw - padding * 2, 200),
                                    Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                                    self._bubble_display)
        bw = min(max_bw, max(80, text_rect.width() + padding * 2 + 4))
        bh = min(140, text_rect.height() + padding * 2 + tail_size + 4)
        bx = (self.width() - bw) // 2; by = margin
        path = QPainterPath()
        path.addRoundedRect(bx, by, bw, bh - tail_size, 10, 10)
        tail_x = bx + bw // 2; tail_y = by + bh - tail_size
        path.moveTo(tail_x - tail_size, tail_y)
        path.lineTo(tail_x, tail_y + tail_size)
        path.lineTo(tail_x + tail_size, tail_y)
        path.closeSubpath()
        painter.fillPath(path, QColor(255, 255, 255, 235))
        painter.setPen(QPen(QColor(theme.BORDER), 1.2))
        painter.drawPath(path)
        painter.setPen(QColor(theme.TEXT))
        ta = QRect(bx + padding, by + padding, bw - padding * 2, bh - tail_size - padding * 2)
        painter.drawText(ta, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self._bubble_display)

    def _load_position(self):
        screen = QApplication.primaryScreen().geometry()
        x, y = self.config.get("pet_x", -1), self.config.get("pet_y", -1)
        if x < 0 or y < 0:
            x = screen.width() - self.width() - 20
            y = screen.height() - self.height() - 60
        self.move(x, y)

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.Antialiasing)
            w, h = self.character.base_size()
            sf, dx, dy, rot = self._current_transform()
            t = QTransform()
            t.translate(self.width() // 2 + dx, 20 + h // 2 + dy)
            t.rotate(rot)
            t.scale(sf, sf)
            if self.character.mode == "single":
                img = self.character.get_single_frame()
            else:
                img = self.sprite_loader.get_frame(self._animation, self._frame)
            qimage = self._pil_to_qimage(img)
            pixmap = QPixmap.fromImage(qimage)
            painter.setTransform(t)
            painter.drawPixmap(-w // 2, -h // 2, w, h, pixmap)
            painter.resetTransform()
            if self._drag_hover:
                painter.setPen(QPen(QColor(53, 116, 240, 120), 3))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPoint(self.width() // 2, 20 + h // 2),
                                    max(w, h) // 2 + 6, max(w, h) // 2 + 6)
            if self.config.get("show_pet_name", False):
                painter.setPen(QColor(theme.TEXT_MUTED))
                painter.setFont(QFont("Microsoft YaHei UI", 7))
                nm = self.config.pet_name
                fm = QFontMetrics(painter.font())
                painter.drawText((self.width() - fm.horizontalAdvance(nm)) // 2,
                                 self.height() - 8, nm)
            if self.config.get("pocket_badge_enabled", True):
                cnt = len(self.pocket.list_items())
                if cnt > 0:
                    self._draw_badge(painter, cnt)
            self._draw_bubble(painter)
            painter.end()
        except Exception as e:
            print(f"Paint error: {e}")
            import traceback
            traceback.print_exc()

    def _current_transform(self):
        if not self._sem_active:
            return 1.0, 0, 0, 0
        nm, pm = self._sem_steps[self._sem_idx]
        if nm == "bob":
            return 1.0, 0, -abs(pm) * 3, 0
        if nm == "squash":
            return pm, 0, 4, 0
        if nm == "bounce":
            return pm, 0, -8 * (pm - 1), 0
        if nm == "tilt":
            return 1.0, 0, 0, pm
        if nm == "shake":
            return 1.0, 8 if self._sem_idx % 2 else -8, 0, 0
        if nm == "pop":
            return pm, 0, 0, 0
        if nm == "slide":
            return 1.0, pm, 0, 0
        return 1.0, 0, 0, 0

    def _draw_badge(self, painter, count):
        txt = str(count) if count <= 99 else "99+"
        sz = 18; x = self.width() - sz - 2; y = 4
        painter.setPen(Qt.NoPen); painter.setBrush(QBrush(QColor(53, 116, 240)))
        painter.drawEllipse(x, y, sz, sz)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei UI", 7, QFont.Bold))
        fm = QFontMetrics(painter.font())
        painter.drawText(x + (sz - fm.horizontalAdvance(txt)) // 2, y + sz - 4, txt)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressing = True
            self._press_pos = event.globalPos()
            self._moved = False
            self._last_activity = time.time()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._pressing and event.buttons() == Qt.LeftButton:
            if not self._moved and (event.globalPos() - self._press_pos).manhattanLength() > QApplication.startDragDistance():
                self._moved = True
                self._dragging = True
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            if self._dragging:
                self.move(event.globalPos() - self._drag_pos)
                self._last_activity = time.time()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressing = False
            if self._dragging:
                self._dragging = False
                self.config.set("pet_x", self.x())
                self.config.set("pet_y", self.y())
            elif not self._moved:
                self._on_single_click()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()

    def _on_single_click(self):
        if self._state == self.STATE_SLEEP:
            self.set_state(self.STATE_IDLE)
        if self._quick_panel is None:
            from quick_panel import QuickPanel
            self._quick_panel = QuickPanel(self)
        if self._quick_panel.isVisible():
            self._quick_panel.hide()
        else:
            self._quick_panel.refresh()
            self._quick_panel.showNear(self)

    def wheelEvent(self, event):
        # Plain wheel zooms when enabled; Ctrl+wheel ALWAYS zooms (reliable resizing).
        ctrl = event.modifiers() & Qt.ControlModifier
        delta = event.angleDelta().y()
        if not ctrl and not self.config.get("wheel_zoom_enabled", True):
            self._scale_debug("wheel_ignored", ctrl=bool(ctrl), angleDelta=delta,
                              reason="wheel_zoom_enabled=false")
            event.ignore()
            return
        # 0.2 per plain notch is clearly visible at every scale (5–20% jump);
        # Ctrl+wheel stays at 0.1 for fine adjustment.
        factor = 0.1 if ctrl else 0.2
        if delta > 0:
            self._change_scale(factor)
        else:
            self._change_scale(-factor)
        event.accept()

    def enterEvent(self, event):
        self._last_activity = time.time()
        if self._state == self.STATE_SLEEP:
            self.set_state(self.STATE_IDLE)

    def dragEnterEvent(self, event):
        paths = self._local_drop_paths(event)
        mime = event.mimeData()
        drop_log.info("dragEnter formats=%s hasUrls=%s urls=%s paths=%s "
                      "proposed=%s possible=%s accepted_before=%s",
                      mime.formats() if mime else [],
                      bool(mime and mime.hasUrls()),
                      mime.urls() if mime and mime.hasUrls() else [],
                      paths,
                      getattr(event, "proposedAction", lambda: None)(),
                      getattr(event, "possibleActions", lambda: None)(),
                      getattr(event, "isAccepted", lambda: None)())
        if paths:
            self._drag_hover = True
            # Force CopyAction (Pocket stores references; never Move from Explorer)
            event.setDropAction(Qt.CopyAction)
            event.accept()
            drop_log.info("dragEnter accepted action=%s accepted_after=%s",
                          getattr(event, "dropAction", lambda: None)(),
                          getattr(event, "isAccepted", lambda: None)())
            self.update()
        else:
            event.ignore()
            drop_log.info("dragEnter rejected accepted_after=%s",
                          getattr(event, "isAccepted", lambda: None)())

    def dragMoveEvent(self, event):
        # Keep accepting valid local files as CopyAction while dragging over.
        paths = self._local_drop_paths(event)
        if paths:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            drop_log.debug("dragMove accepted paths=%s action=%s",
                           paths, getattr(event, "dropAction", lambda: None)())
        else:
            event.ignore()
            drop_log.debug("dragMove rejected")

    def dragLeaveEvent(self, event):
        self._drag_hover = False
        self.update()

    def dropEvent(self, event):
        self._drag_hover = False
        self.update()
        paths = self._local_drop_paths(event)
        if not paths:
            event.ignore()
            return
        added = 0
        duplicates = 0
        failures = 0
        for p in paths:
            before = len(self.pocket.list_items())
            try:
                item = self.pocket.add(p)
                if len(self.pocket.list_items()) == before:
                    duplicates += 1
                else:
                    added += 1
                    if p.is_dir():
                        self.file_watch.watch(p)
                drop_log.info("drop add path=%s result=%s duplicate=%s",
                              p, item.id, len(self.pocket.list_items()) == before)
            except (OSError, ValueError) as exc:
                failures += 1
                drop_log.warning("drop add failed path=%s error=%s", p, exc)
                continue
        if added:
            self.events.dispatch(AppEvent("pocket", "receive", {"count": added}))
            self.play_semantic("RECEIVE_FILE")
            d = f"（{duplicates}个已存在）" if duplicates else ""
            self.show_bubble(f"已放入口袋 · {added}{d}", 4500)
            QTimer.singleShot(3000, lambda: self.set_state(self.STATE_IDLE))
        elif duplicates:
            self.show_bubble("已在口袋中", 3000)
        else:
            self.show_bubble("无法添加这些项目", 3500)
        event.setDropAction(Qt.CopyAction)
        event.accept()
        drop_log.info("drop complete paths=%s added=%s duplicates=%s failures=%s "
                      "action=%s accepted=%s",
                      paths, added, duplicates, failures,
                      getattr(event, "dropAction", lambda: None)(),
                      getattr(event, "isAccepted", lambda: None)())

    @staticmethod
    def _local_drop_paths(event):
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            return []
        out = []
        for u in mime.urls():
            if u.isLocalFile():
                p = Path(u.toLocalFile())
                try:
                    if p.exists():
                        out.append(p)
                except OSError:
                    continue
        return out

    def play_semantic(self, semantic):
        if self.character.mode == "sheet":
            self.play_animation(self._SHEET_MAP.get(semantic, "RestPose"))
            return
        steps = self.character.animation_steps(semantic)
        if not steps:
            return
        self._sem_steps = steps
        self._sem_idx = 0
        self._sem_active = True
        self._sem_timer.start(STEP_MS)
        self.update()

    def _sem_tick(self):
        self._sem_idx += 1
        if self._sem_idx < len(self._sem_steps):
            self._sem_timer.start(STEP_MS)
        else:
            self._finish_semantic()
        self.update()

    def _finish_semantic(self):
        self._sem_active = False
        self._sem_steps = []
        self._sem_idx = -1
        if self._state != self.STATE_SLEEP:
            self._state = self.STATE_IDLE
        self.update()

    def _animate(self):
        self._frame += 1
        self.update()
        if self._frame < self.sprite_loader.get_frame_count(self._animation):
            self._schedule_next_frame()
        else:
            self._animation = "RestPose"
            self._frame = 0
            if self._state != self.STATE_SLEEP:
                self._state = self.STATE_IDLE
            self.update()

    def play_animation(self, animation):
        self._animation = animation if animation in ANIMATIONS else "RestPose"
        self._frame = 0
        self.update()
        self._schedule_next_frame()

    def _schedule_idle_variety(self):
        self._idle_variety_timer.start(random.randint(15000, 30000))

    def _play_idle_variety(self):
        if self._state == self.STATE_IDLE and self._animation == "RestPose":
            self.play_animation(random.choice(["Idle1_1", "IdleSideToSide",
                                               "IdleFingerTap", "IdleEyeBrowRaise"]))
        self._schedule_idle_variety()

    def set_state(self, state):
        if state != self._state:
            self._state = state
        if self.character.mode == "sheet":
            self.play_animation({self.STATE_IDLE: "RestPose",
                                 self.STATE_TALKING: "Explain",
                                 self.STATE_ALERT: "Alert",
                                 self.STATE_SLEEP: "IdleSnooze"}.get(state, "RestPose"))
        else:
            self.update()

    def _check_idle(self):
        if self._state == self.STATE_SLEEP:
            return
        if time.time() - self._last_activity > 300:
            self.set_state(self.STATE_SLEEP)
            self.show_bubble_now("我先休息一下，需要时点我~", 4000)

    def _schedule_next_reminder(self):
        self._remind_timer.stop()
        da = self.reminder.next_due_at()
        if da is None:
            return
        self._remind_timer.start(min(max(0, int((da - datetime.now()).total_seconds() * 1000)), 2147000000))

    def _check_due_reminders(self):
        self.reminder.check_due()
        self._schedule_next_reminder()

    def _application_state_changed(self, state):
        if state == Qt.ApplicationActive:
            self._check_due_reminders()

    def _on_reminder_due(self, reminder):
        self.events.dispatch(AppEvent("reminder", "due", reminder))
        if self.config.get("reminder_sound_enabled", True):
            sounds.play_reminder()
        if self.config.get("reminder_bubble_enabled", True):
            self.play_semantic("REMINDER")
            self.show_bubble(f"提醒：{reminder.content}", 10000)
        QTimer.singleShot(3000, lambda: self.set_state(self.STATE_IDLE))

    def _schedule_next_wage_wake(self):
        """Schedule exactly one wake at the next key wage moment.

        Replaces the old permanent 60s poll: the app now sleeps until one of
        work_start / lunch boundaries / 17:30 / 20:00 / the next income
        notification slot (or at most 1h, to pick up settings changes), then
        reschedules. TodayWageWindow keeps its own 1s refresh timer but only
        while it is visible.
        """
        svc = self.wage
        now = svc._now()
        candidates = []
        if svc.configured:
            day = now.date()
            for _ in range(2):
                for name in ("work_start", "lunch_start", "lunch_end",
                             "overtime_start", "meal_allowance_time"):
                    t = getattr(svc.settings, name)
                    moment = datetime.combine(day, t)
                    if moment > now:
                        candidates.append(moment)
                day = day.fromordinal(day.toordinal() + 1)
            interval = svc.settings.income_interval_minutes
            if interval:
                slot_secs = interval * 60
                next_slot = (int(now.timestamp()) // slot_secs + 1) * slot_secs
                candidates.append(datetime.fromtimestamp(next_slot))
        if not candidates:
            # Unconfigured or nothing scheduled: check again in an hour.
            candidates.append(now + timedelta(hours=1))
        next_moment = min(candidates)
        delay_ms = max(1000, int((next_moment - now).total_seconds() * 1000))
        self._wage_timer.start(min(delay_ms, 3600 * 1000))

    def _on_wage_wake(self):
        try:
            self._check_wage_progress()
        finally:
            self._schedule_next_wage_wake()

    def _check_wage_progress(self):
        snapshot = self.wage.current_breakdown()
        overtime = snapshot.overtime_minutes > 0
        if overtime and not self._wage_last_overtime:
            self.play_semantic("OVERTIME_START")
            self.show_bubble("开始加班", 3500)
        self._wage_last_overtime = overtime
        self.wage.maybe_emit_progress()

    def _prompt_missing_clockout(self, day):
        """Three-action prompt for yesterday's missing clock-out (non-modal)."""
        from wage.ui_missing import MissingClockoutDialog
        dlg = MissingClockoutDialog(self.wage, day, self)
        dlg.accepted.connect(self._on_clockout_record_changed)
        dlg.show()
        dlg.raise_()

    def _on_clockout_record_changed(self):
        if self._quick_panel is not None:
            self._quick_panel.refresh()
        if getattr(self, "_today_wage", None) is not None:
            self._today_wage.refresh()

    def _on_wage_progress(self, snapshot):
        self.play_semantic("WAGE_PROGRESS")
        if self.wage.settings.privacy_mode:
            self.show_bubble(f"今日进度 {snapshot.progress}%", 5000)
        else:
            self.show_bubble(f"今天已赚 ¥{snapshot.total_earned:.2f}\n进度 {snapshot.progress}%", 5000)

    def _clock_out(self, actual_clock_out=None):
        """Save today's actual clock-out; exposed for the assistant panel."""
        if actual_clock_out is None:
            actual_clock_out = self.wage._now()
        record = self.wage.record_clock_out(actual_clock_out)
        self.play_semantic("CLOCK_OUT")
        if record.meal_allowance:
            self.play_semantic("MEAL_ALLOWANCE")
        if self.wage.settings.privacy_mode:
            self.show_bubble(f"{record.actual_clock_out:%H:%M} 下班已记录", 4500)
        else:
            self.show_bubble(f"{record.actual_clock_out:%H:%M} 下班\n加班 {record.overtime_minutes // 60}h{record.overtime_minutes % 60:02d}m", 4500)
        if self._today_wage is not None:
            self._today_wage.refresh()

    def _handle_app_event(self, event):
        if not self.config.get("file_event_animations_enabled", True):
            return
        anim = self.animation_controller.resolve(event)
        self._state = self.STATE_ALERT if event.category == "reminder" else self.STATE_TALKING
        if anim:
            self.play_semantic(anim)

    def _on_shell_event(self, event):
        import logging
        _log = logging.getLogger("pet.shell_callback")
        _log.info("_on_shell_event RECEIVED action=%s path=%s", event.action, event.path)
        if not self.config.get("file_event_animations_enabled", True):
            return
        # V3.2: removed is_explorer_foreground() gate — it was too strict
        # and blocked legitimate Explorer delete/create events.
        action_map = {"created": "CREATE_FILE", "deleted": "DELETE_FILE",
                      "renamed": "RENAME_FILE", "dir_created": "CREATE_FILE",
                      "dir_removed": "DELETE_FILE", "dir_renamed": "RENAME_FILE"}
        semantic = action_map.get(event.action)
        if semantic:
            self._state = self.STATE_TALKING
            self.play_semantic(semantic)
            self.show_bubble("检测到文件操作", 2000)
            QTimer.singleShot(2500, lambda: self.set_state(self.STATE_IDLE))

    def _open_add_reminder(self):
        d = AddReminderDialog(self)
        if d.exec_():
            c, dt = d.values()
            self.reminder.add_reminder(c, dt)
            self._schedule_next_reminder()
            self.show_bubble("提醒已保存", 4000)

    def _open_reminders(self):
        ReminderListDialog(self.reminder, self).exec_()
        self._schedule_next_reminder()

    def _open_pocket(self):
        from pocket_window import PocketWindow
        if self._pocket_window is None:
            self._pocket_window = PocketWindow(self.pocket, event_dispatcher=self.events)
        self._pocket_window.refresh()
        self._pocket_window.show_near(self.visible_pet_global_rect())
        if self._quick_panel is not None:
            self._quick_panel.hide()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.show_bubble("Hi! 👋", 2500)
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _show_context_menu(self, pos):
        m = QMenu(self)
        wa = m.addAction("今日收入")
        ca = m.addAction("工时日历")
        m.addSeparator()
        pa = m.addAction("文件口袋")
        aa = m.addAction("新建提醒")
        ra = m.addAction("我的提醒")
        m.addSeparator()
        sa = m.addAction("设置")
        m.addSeparator()
        qa = m.addAction("退出")
        act = m.exec_(pos)
        if act == wa:
            self._open_today_wage()
        elif act == ca:
            self._open_calendar()
        elif act == aa:
            self._open_add_reminder()
        elif act == ra:
            self._open_reminders()
        elif act == pa:
            self._open_pocket()
        elif act == sa:
            self._open_settings()
        elif act == qa:
            self._quit_app()

    def _open_settings(self):
        d = SettingsDialog(self.config, self)
        if d.exec_():
            self._update_from_settings()

    def _open_wage_settings(self):
        from wage.ui_settings import WageSettingsDialog
        d = WageSettingsDialog(self.wage, self)
        if d.exec_():
            self._schedule_next_wage_wake()
            if self._quick_panel is not None:
                self._quick_panel.refresh()
            if getattr(self, "_today_wage", None) is not None:
                self._today_wage.refresh()

    def _open_today_wage(self):
        from wage.ui_today import TodayWageWindow
        if not hasattr(self, "_today_wage") or self._today_wage is None:
            self._today_wage = TodayWageWindow(self.wage, self)
        self._today_wage.refresh()
        self._today_wage.show_near(self.visible_pet_global_rect(), self.screen())
        if self._quick_panel is not None:
            self._quick_panel.hide()

    def _open_calendar(self):
        from wage.ui_calendar import WorkCalendarDialog
        dialog = WorkCalendarDialog(self.wage, self)
        dialog.exec_()
        if self._quick_panel is not None:
            self._quick_panel.refresh()

    def _reload_character_preview(self):
        # live character change during settings dialog
        try:
            self.character.reload()
            self._resize_to_character()
            self.update()
        except Exception:
            pass

    def _update_from_settings(self):
        self.tray_icon.setToolTip(f"{self.config.pet_name} — 桌面助手")
        was_visible = self.isVisible()
        old_pos = self.pos()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        # setWindowFlags() hides a native top-level widget. Preserve the
        # user's current visibility and position when applying settings.
        self.move(old_pos)
        if was_visible:
            self.show()
            self.raise_()
        self.character.set_scale(float(self.config.get("pet_scale", 3)))
        self.character.reload()
        self._resize_to_character()

    def _update_scale_preview(self, scale):
        self._scale_debug("settings_preview", old=float(self.config.get("pet_scale", 3)), new=float(scale))
        self.character.set_scale(float(scale))
        self._resize_to_character()

    def _scale_debug(self, source, **fields):
        """Optional scaling diagnostics (PET_SCALE_DEBUG=1). Never logs wages."""
        import os
        if os.environ.get("PET_SCALE_DEBUG") != "1":
            return
        w, h = self.character.base_size()
        vpr = self.visible_pet_rect()
        logging.getLogger("pet.scale.debug").info(
            "source=%s cfg_scale=%s char_scale=%s base_size=%dx%d win=%dx%d visible_rect=%dx%d %s",
            source, self.config.get("pet_scale"), self.character.scale,
            w, h, self.width(), self.height(), vpr.width(), vpr.height(),
            " ".join(f"{k}={v}" for k, v in fields.items()))

    def _resize_to_character(self):
        w, h = self.character.base_size()
        self._pet_w, self._pet_h = w, h
        self.setFixedSize(w + 40, h + 60)
        self._reposition_attached_panels(reposition_quick=True, reposition_pocket=True)
        self._position_bubble()

    def _change_scale(self, delta):
        current = float(self.config.get("pet_scale", 3))
        ns = max(1.0, min(6.0, round(current + delta, 2)))
        self.config.set("pet_scale", ns)
        self.character.set_scale(ns)
        self._resize_to_character()
        self._scale_debug("wheel_change", delta=delta, old=current, new=ns)

    def _pil_to_qimage(self, pi):
        if pi.mode != "RGBA":
            pi = pi.convert("RGBA")
        data = pi.tobytes("raw", "RGBA")
        return QImage(data, pi.width, pi.height, QImage.Format_RGBA8888)

    # ── Bug4: attached panels follow the pet ───────────────────────────────
    def moveEvent(self, event):
        super().moveEvent(event)
        self._reposition_attached_panels()
        self._position_bubble()

    def _reposition_attached_panels(self, reposition_quick=None, reposition_pocket=None):
        if reposition_quick is None:
            reposition_quick = (self._quick_panel is not None
                                and self._quick_panel.isVisible())
        if reposition_pocket is None:
            reposition_pocket = (self._pocket_window is not None
                                  and self._pocket_window.isVisible())
        reposition_today = (getattr(self, '_today_wage', None) is not None
                            and self._today_wage.isVisible())
        # Never dereference a panel that doesn't exist yet.
        reposition_quick = reposition_quick and self._quick_panel is not None
        reposition_pocket = reposition_pocket and self._pocket_window is not None
        if not reposition_quick and not reposition_pocket and not reposition_today:
            return
        # Anchor panels to the VISIBLE character pixels, not the transparent
        # PetWindow rectangle, so the 8px gap is measured from the sprite edge.
        geo = self.visible_pet_global_rect()
        if reposition_quick:
            self._quick_panel.move_near(geo, live=True)
        if reposition_pocket:
            self._pocket_window.move_near(geo, live=True)
        if reposition_today:
            self._today_wage.move_near(self.visible_pet_global_rect(), screen=self.screen(), live=True)

    def _quit_app(self):
        if self._shell_watcher:
            self._shell_watcher.stop()
        if self._quick_panel is not None:
            self._quick_panel.close()
        if self._pocket_window is not None:
            self._pocket_window.close()
        if getattr(self, "_today_wage", None) is not None:
            self._today_wage.close()
        self.file_watch.stop_all()
        self._bubble_hide()
        if self._bubble_window is not None:
            self._bubble_window.close()
        self.tray_icon.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Pet")
    app.setQuitOnLastWindowClosed(False)
    app.setFont(theme.font())
    app.setStyleSheet(theme.app_qss())
    config = Config()
    window = PetWindow(config)
    window.show()
    if config.get("show_welcome", True):
        QTimer.singleShot(1200, lambda: (
            window.show_bubble("欢迎使用桌面助手\n① 拖文件到角色：临时寄存\n② 单击角色：打开文件口袋\n③ 右键角色：提醒和设置", 10000),
            window.set_state(PetWindow.STATE_TALKING),
            QTimer.singleShot(2000, lambda: window.set_state(PetWindow.STATE_IDLE)),
        ))
        config.set("show_welcome", False)
    return app.exec_()
