"""
Desktop Pet Window — V2: unified theme, single-image character, Chinese UI.
"""
import math, random, sys, time
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize, pyqtSignal, QThread
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
import sounds, theme


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        box = QGroupBox("角色"); form = QVBoxLayout(box)
        row_img = QHBoxLayout()
        self.image_label = QLabel(); self.image_label.setFixedSize(64,64)
        self.image_label.setAlignment(Qt.AlignCenter); row_img.addWidget(self.image_label)
        col_btn = QVBoxLayout()
        self.import_button = QPushButton("选择图片...")
        self.reset_button = QPushButton("恢复默认角色")
        col_btn.addWidget(self.import_button); col_btn.addWidget(self.reset_button)
        col_btn.addStretch(); row_img.addLayout(col_btn); row_img.addStretch()
        form.addLayout(row_img)
        row_scale = QHBoxLayout(); row_scale.addWidget(QLabel("大小"))
        self.scale_slider = QSlider(Qt.Horizontal); self.scale_slider.setRange(10,60)
        self.scale_slider.setValue(int(self.config.get("pet_scale", 3.0) * 10))
        self.scale_slider.setTickPosition(QSlider.TicksBelow)
        row_scale.addWidget(self.scale_slider, 1); form.addLayout(row_scale)
        self.name_check = QCheckBox("显示角色名称")
        self.name_check.setChecked(self.config.get("show_pet_name", False))
        form.addWidget(self.name_check); layout.addWidget(box)
        box2 = QGroupBox("行为"); bl = QVBoxLayout(box2)
        self.top_check = QCheckBox("始终置顶"); self.top_check.setChecked(self.config.get("always_on_top", True))
        self.wheel_check = QCheckBox("允许滚轮调整角色大小（容易误操作）"); self.wheel_check.setChecked(self.config.get("wheel_zoom_enabled", False))
        self.anim_check = QCheckBox("文件操作时播放动画"); self.anim_check.setChecked(self.config.get("file_event_animations_enabled", True))
        self.badge_check = QCheckBox("口袋数量角标"); self.badge_check.setChecked(self.config.get("pocket_badge_enabled", True))
        for w in (self.top_check, self.wheel_check, self.anim_check, self.badge_check): bl.addWidget(w)
        layout.addWidget(box2)
        box3 = QGroupBox("提醒"); rl = QVBoxLayout(box3)
        self.sound_check = QCheckBox("提醒声音"); self.sound_check.setChecked(self.config.get("reminder_sound_enabled", True))
        self.bubble_check = QCheckBox("桌宠气泡"); self.bubble_check.setChecked(self.config.get("reminder_bubble_enabled", True))
        rl.addWidget(self.sound_check); rl.addWidget(self.bubble_check); layout.addWidget(box3)
        box4 = QGroupBox("数据"); dl = QHBoxLayout(box4)
        dl.addWidget(QPushButton("打开数据目录")); dl.addWidget(QPushButton("打开日志目录")); dl.addStretch()
        layout.addWidget(box4)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.import_button.clicked.connect(self._import_image)
        self.reset_button.clicked.connect(self._reset_image)

    def _refresh_preview(self):
        from character import draw_default_buddy; from paths import PROJECT_ROOT
        from PIL.ImageQt import ImageQt
        name = self.config.get("character_image", ""); img = None
        if name:
            path = PROJECT_ROOT / "assets" / name
            if path.exists():
                try:
                    from PIL import Image as PILImage; img = PILImage.open(path).convert("RGBA")
                except OSError: img = None
        if img is None: img = draw_default_buddy()
        self.image_label.setPixmap(QPixmap.fromImage(ImageQt(img)).scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def _import_image(self):
        from character import import_character_image; from paths import PROJECT_ROOT
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self,"选择角色图片","","图片 (*.png *.webp)")
        if not path: return
        try: name = import_character_image(Path(path), PROJECT_ROOT / "assets")
        except ValueError as exc: QMessageBox.warning(self,"导入失败",str(exc)); return
        self.config.set("character_image", name); self.config.set("character_mode", "single"); self._refresh_preview()
    def _reset_image(self):
        self.config.set("character_image", ""); self._refresh_preview()
    def _save(self):
        c = self.config; c.set("pet_scale", self.scale_slider.value()/10.0)
        c.set("show_pet_name", self.name_check.isChecked()); c.set("always_on_top", self.top_check.isChecked())
        c.set("wheel_zoom_enabled", self.wheel_check.isChecked()); c.set("file_event_animations_enabled", self.anim_check.isChecked())
        c.set("pocket_badge_enabled", self.badge_check.isChecked()); c.set("reminder_sound_enabled", self.sound_check.isChecked())
        c.set("reminder_bubble_enabled", self.bubble_check.isChecked()); self.accept()


class PetWindow(QWidget):
    STATE_IDLE="idle"; STATE_TALKING="talking"; STATE_ALERT="alert"; STATE_SLEEP="sleep"
    _SHEET_MAP = {"REMINDER":"Alert","RECEIVE_FILE":"Save","GIVE_FILE":"SendMail","DELETE_FILE":"EmptyTrash",
        "CREATE_FILE":"Show","RENAME_FILE":"Searching","COPY_FILE":"Print","MOVE_FILE":"SendMail","SUCCESS":"Save","ERROR":"GetAttention"}

    def __init__(self, config):
        super().__init__()
        self.config=config; self.reminder=ReminderService(); self.pocket=PocketService()
        self.file_watch=FileWatchService(); self.events=EventDispatcher(self)
        self.animation_controller=AnimationController(set(AnimationController.MAPPING.values()) - {None})
        self.events.event_received.connect(self._handle_app_event)
        self.file_watch.on_change=lambda c:self.events.dispatch(AppEvent("windows",c.action,c))
        self.character=CharacterController(config,scale=config.get("pet_scale",3))
        self._state=self.STATE_IDLE; self._animation="RestPose"; self._frame=0
        self._drag_pos=QPoint(); self._dragging=False; self._pressing=False
        self._press_pos=QPoint(); self._moved=False; self._drag_hover=False
        self._sem_steps=[]; self._sem_idx=-1; self._sem_active=False
        self._sem_timer=QTimer(self); self._sem_timer.setSingleShot(True); self._sem_timer.timeout.connect(self._sem_tick)
        w,h=self.character.base_size(); self._pet_w,self._pet_h=w,h
        self._setup_window(); self._setup_tray(); self._setup_timers(); self._setup_callbacks()
        self._setup_speech_bubble(); self._load_position()
        QApplication.instance().applicationStateChanged.connect(self._application_state_changed)

    def _setup_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground); self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose,False); self.setAcceptDrops(True)
        self.setFixedSize(self._pet_w+40,self._pet_h+60); self.setMouseTracking(True)

    def _setup_tray(self):
        self.tray_icon=QSystemTrayIcon(self)
        from paths import PROJECT_ROOT; icon_path=PROJECT_ROOT/"assets"/"app.ico"
        self.tray_icon.setIcon(QIcon(str(icon_path)) if icon_path.exists() else QIcon(self._draw_tray_icon()))
        self.tray_icon.setToolTip(f"{self.config.pet_name} — 桌面助手")
        m=QMenu(); m.addAction("显示/隐藏角色").triggered.connect(self._toggle_visibility)
        m.addAction("文件口袋").triggered.connect(self._open_pocket); m.addAction("新建提醒").triggered.connect(self._open_add_reminder)
        m.addAction("我的提醒").triggered.connect(self._open_reminders); m.addSeparator()
        m.addAction("设置").triggered.connect(self._open_settings); m.addSeparator()
        m.addAction("退出").triggered.connect(self._quit_app)
        self.tray_icon.setContextMenu(m); self.tray_icon.show()
        self.tray_icon.activated.connect(self._tray_activated)

    @staticmethod
    def _draw_tray_icon():
        pix=QPixmap(32,32); pix.fill(Qt.transparent); p=QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(100,100,120),1.5)); p.setBrush(QBrush(QColor(200,210,230)))
        p.drawRoundedRect(5,10,22,18,3,3); p.drawArc(10,2,12,16,0,-180*16); p.end(); return pix

    def _toggle_visibility(self):
        if self.isVisible(): self.hide()
        else: self.show(); self.raise_()

    def _setup_timers(self):
        self._anim_timer=QTimer(self); self._anim_timer.timeout.connect(self._animate); self._anim_timer.setSingleShot(True)
        self._idle_variety_timer=QTimer(self); self._idle_variety_timer.timeout.connect(self._play_idle_variety); self._idle_variety_timer.setSingleShot(True)
        if self.config.get("character_mode","single")=="sheet" and self.config.get("idle_animations_enabled",False):
            self._schedule_next_frame(); self._schedule_idle_variety()
        self._remind_timer=QTimer(self); self._remind_timer.setSingleShot(True); self._remind_timer.timeout.connect(self._check_due_reminders)
        self._idle_timer=QTimer(self); self._idle_timer.timeout.connect(self._check_idle); self._idle_timer.start(60000); self._last_activity=time.time()

    def _schedule_next_frame(self):
        dur=self.sprite_loader.get_duration(self._animation,self._frame); self._anim_timer.start(max(16,min(2000,dur)))
    def _setup_callbacks(self):
        self.reminder.on_reminder_due=self._on_reminder_due; self._schedule_next_reminder()
    def _setup_speech_bubble(self):
        self._bubble_text=""; self._bubble_display=""; self._bubble_char=0; self._bubble_visible=False
        self._bubble_dismiss_ms=6000; self._bubble_timer=QTimer(self); self._bubble_timer.timeout.connect(self._bubble_type)
        self._bubble_dismiss=QTimer(self); self._bubble_dismiss.timeout.connect(self._bubble_hide); self._bubble_dismiss.setSingleShot(True)
    def _bubble_type(self):
        self._bubble_char=len(self._bubble_text); self._bubble_display=self._bubble_text; self._bubble_timer.stop(); self.update()
    def _bubble_hide(self):
        self._bubble_visible=False; self._bubble_timer.stop(); self._bubble_dismiss.stop(); self.update()
    def show_bubble(self, text, auto_dismiss_ms=6000):
        self._bubble_text=text; self._bubble_display=text; self._bubble_char=len(text)
        self._bubble_visible=True; self._bubble_dismiss_ms=auto_dismiss_ms
        if auto_dismiss_ms>0: self._bubble_dismiss.start(auto_dismiss_ms)
        self.update()
    def show_bubble_now(self, text, auto_dismiss_ms=5000):
        self._bubble_text=text; self._bubble_display=text; self._bubble_char=len(text)
        self._bubble_visible=True; self._bubble_dismiss_ms=auto_dismiss_ms; self._bubble_dismiss.stop()
        if auto_dismiss_ms>0: self._bubble_dismiss.start(auto_dismiss_ms)
        self.update()
    def _draw_bubble(self, painter):
        if not self._bubble_visible or not self._bubble_display: return
        margin=5; max_bw=self.width()-margin*2; padding=10; tail_size=8
        font=QFont("Microsoft YaHei UI",8); painter.setFont(font); fm=QFontMetrics(font)
        text_rect=fm.boundingRect(QRect(0,0,max_bw-padding*2,200),Qt.TextWordWrap|Qt.AlignLeft|Qt.AlignTop,self._bubble_display)
        bw=min(max_bw,max(80,text_rect.width()+padding*2+4)); bh=min(140,text_rect.height()+padding*2+tail_size+4)
        bx=(self.width()-bw)//2; by=margin; path=QPainterPath()
        path.addRoundedRect(bx,by,bw,bh-tail_size,10,10)
        tail_x=bx+bw//2; tail_y=by+bh-tail_size; path.moveTo(tail_x-tail_size,tail_y)
        path.lineTo(tail_x,tail_y+tail_size); path.lineTo(tail_x+tail_size,tail_y); path.closeSubpath()
        painter.fillPath(path,QColor(255,255,255,235)); painter.setPen(QPen(QColor(theme.BORDER),1.2)); painter.drawPath(path)
        painter.setPen(QColor(theme.TEXT)); ta=QRect(bx+padding,by+padding,bw-padding*2,bh-tail_size-padding*2)
        painter.drawText(ta,Qt.TextWordWrap|Qt.AlignLeft|Qt.AlignTop,self._bubble_display)

    def _load_position(self):
        screen=QApplication.primaryScreen().geometry(); x,y=self.config.get("pet_x",-1),self.config.get("pet_y",-1)
        if x<0 or y<0: x=screen.width()-self.width()-20; y=screen.height()-self.height()-60
        self.move(x,y)

    def paintEvent(self, event):
        try:
            painter=QPainter(self); painter.setRenderHint(QPainter.SmoothPixmapTransform); painter.setRenderHint(QPainter.Antialiasing)
            w,h=self.character.base_size(); sf,dx,dy,rot=self._current_transform()
            t=QTransform(); t.translate(self.width()//2,20+h//2); t.rotate(rot); t.scale(sf,sf)
            if self.character.mode=="single": img=self.character.get_single_frame()
            else: img=self.sprite_loader.get_frame(self._animation,self._frame)
            qimage=self._pil_to_qimage(img); pixmap=QPixmap.fromImage(qimage)
            painter.setTransform(t); painter.drawPixmap(-w//2,-h//2,w,h,pixmap); painter.resetTransform()
            if self._drag_hover:
                painter.setPen(QPen(QColor(53,116,240,120),3)); painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPoint(self.width()//2,20+h//2),max(w,h)//2+6,max(w,h)//2+6)
            if self.config.get("show_pet_name",False):
                painter.setPen(QColor(theme.TEXT_MUTED)); painter.setFont(QFont("Microsoft YaHei UI",7))
                nm=self.config.pet_name; fm=QFontMetrics(painter.font())
                painter.drawText((self.width()-fm.horizontalAdvance(nm))//2,self.height()-8,nm)
            if self.config.get("pocket_badge_enabled",True):
                cnt=len(self.pocket.list_items())
                if cnt>0: self._draw_badge(painter,cnt)
            self._draw_bubble(painter); painter.end()
        except Exception as e:
            print(f"Paint error: {e}"); import traceback; traceback.print_exc()

    def _current_transform(self):
        if not self._sem_active: return 1.0,0,0,0
        nm,pm=self._sem_steps[self._sem_idx]
        if nm=="bob": return 1.0,0,-abs(pm)*3,0
        if nm=="squash": return pm,0,4,0
        if nm=="bounce": return pm,0,-8*(pm-1),0
        if nm=="tilt": return 1.0,0,0,pm
        if nm=="shake": return 1.0,8 if self._sem_idx%2 else -8,0,0
        if nm=="pop": return pm,0,0,0
        if nm=="slide": return 1.0,pm,0,0
        return 1.0,0,0,0

    def _draw_badge(self, painter, count):
        txt=str(count) if count<=99 else "99+"; sz=18; x=self.width()-sz-2; y=4
        painter.setPen(Qt.NoPen); painter.setBrush(QBrush(QColor(53,116,240)))
        painter.drawEllipse(x,y,sz,sz); painter.setPen(QColor(255,255,255))
        painter.setFont(QFont("Microsoft YaHei UI",7,QFont.Bold))
        fm=QFontMetrics(painter.font()); painter.drawText(x+(sz-fm.horizontalAdvance(txt))//2,y+sz-4,txt)

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            self._pressing=True; self._press_pos=event.globalPos(); self._moved=False; self._last_activity=time.time(); event.accept()
        elif event.button()==Qt.RightButton: self._show_context_menu(event.globalPos()); event.accept()
    def mouseMoveEvent(self,event):
        if self._pressing and event.buttons()==Qt.LeftButton:
            if not self._moved and (event.globalPos()-self._press_pos).manhattanLength()>QApplication.startDragDistance():
                self._moved=True; self._dragging=True; self._drag_pos=event.globalPos()-self.frameGeometry().topLeft()
            if self._dragging: self.move(event.globalPos()-self._drag_pos); self._last_activity=time.time()
            event.accept()
    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton:
            self._pressing=False
            if self._dragging: self._dragging=False; self.config.set("pet_x",self.x()); self.config.set("pet_y",self.y())
            elif not self._moved: self._on_single_click()
            event.accept()
    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.LeftButton: event.accept()
    def _on_single_click(self):
        """Single click on pet — toggle quick panel."""
        if self._state==self.STATE_SLEEP: self.set_state(self.STATE_IDLE)
        if not hasattr(self, "_quick_panel"):
            from quick_panel import QuickPanel
            self._quick_panel = QuickPanel(self)
        if self._quick_panel.isVisible():
            self._quick_panel.hide()
        else:
            self._quick_panel.refresh()
            self._quick_panel.showNear(self)
    def wheelEvent(self,event):
        if not self.config.get("wheel_zoom_enabled",False): event.ignore(); return
        if event.angleDelta().y()>0: self._change_scale(0.1)
        else: self._change_scale(-0.1)
        event.accept()
    def enterEvent(self,event):
        self._last_activity=time.time()
        if self._state==self.STATE_SLEEP: self.set_state(self.STATE_IDLE)
    def dragEnterEvent(self,event):
        if self._local_drop_paths(event): self._drag_hover=True; event.acceptProposedAction(); self.update()
        else: event.ignore()
    def dragLeaveEvent(self,event): self._drag_hover=False; self.update()
    def dropEvent(self,event):
        self._drag_hover=False; self.update()
        paths=self._local_drop_paths(event)
        if not paths: event.ignore(); return
        added=0; duplicates=0
        for p in paths:
            before=len(self.pocket.list_items())
            try:
                self.pocket.add(p)
                if len(self.pocket.list_items())==before: duplicates+=1
                else: added+=1
                if p.is_dir(): self.file_watch.watch(p)
            except (OSError,ValueError): continue
        if added:
            self.events.dispatch(AppEvent("pocket","receive",{"count":added})); self.play_semantic("RECEIVE_FILE")
            d=f"（{duplicates}个已存在）" if duplicates else ""; self.show_bubble(f"已放入口袋 · {added}{d}",4500)
            QTimer.singleShot(3000,lambda:self.set_state(self.STATE_IDLE))
        elif duplicates: self.show_bubble("已在口袋中",3000)
        else: self.show_bubble("无法添加这些项目",3500)
        event.acceptProposedAction()
    @staticmethod
    def _local_drop_paths(event):
        mime=event.mimeData()
        if not mime.hasUrls(): return []
        return [Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile() and Path(u.toLocalFile()).exists()]

    def play_semantic(self,semantic):
        if self.character.mode=="sheet": self.play_animation(self._SHEET_MAP.get(semantic,"RestPose")); return
        steps=self.character.animation_steps(semantic)
        if not steps: return
        self._sem_steps=steps; self._sem_idx=0; self._sem_active=True; self._sem_timer.start(STEP_MS); self.update()
    def _sem_tick(self):
        self._sem_idx+=1
        if self._sem_idx<len(self._sem_steps): self._sem_timer.start(STEP_MS)
        else: self._finish_semantic()
        self.update()
    def _finish_semantic(self):
        self._sem_active=False; self._sem_steps=[]; self._sem_idx=-1
        if self._state!=self.STATE_SLEEP: self._state=self.STATE_IDLE
        self.update()
    def _animate(self):
        self._frame+=1; self.update()
        if self._frame<self.sprite_loader.get_frame_count(self._animation): self._schedule_next_frame()
        else: self._animation="RestPose"; self._frame=0
        if self._state!=self.STATE_SLEEP: self._state=self.STATE_IDLE
        self.update()
    def play_animation(self,animation):
        self._animation=animation if animation in ANIMATIONS else "RestPose"
        self._frame=0; self.update(); self._schedule_next_frame()
    def _schedule_idle_variety(self):
        self._idle_variety_timer.start(random.randint(15000,30000))
    def _play_idle_variety(self):
        if self._state==self.STATE_IDLE and self._animation=="RestPose":
            self.play_animation(random.choice(["Idle1_1","IdleSideToSide","IdleFingerTap","IdleEyeBrowRaise"]))
        self._schedule_idle_variety()
    def set_state(self,state):
        if state!=self._state: self._state=state
        if self.character.mode=="sheet":
            self.play_animation({self.STATE_IDLE:"RestPose",self.STATE_TALKING:"Explain",self.STATE_ALERT:"Alert",self.STATE_SLEEP:"IdleSnooze"}.get(state,"RestPose"))
        else: self.update()
    def _check_idle(self):
        if self._state==self.STATE_SLEEP: return
        if time.time()-self._last_activity>300:
            self.set_state(self.STATE_SLEEP); self.show_bubble_now("我先休息一下，需要时点我~",4000)
    def _schedule_next_reminder(self):
        self._remind_timer.stop(); da=self.reminder.next_due_at()
        if da is None: return
        self._remind_timer.start(min(max(0,int((da-datetime.now()).total_seconds()*1000)),2147000000))
    def _check_due_reminders(self): self.reminder.check_due(); self._schedule_next_reminder()
    def _application_state_changed(self,state):
        if state==Qt.ApplicationActive: self._check_due_reminders()
    def _on_reminder_due(self,reminder):
        self.events.dispatch(AppEvent("reminder","due",reminder))
        if self.config.get("reminder_sound_enabled",True): sounds.play_reminder()
        if self.config.get("reminder_bubble_enabled",True):
            self.play_semantic("REMINDER"); self.show_bubble(f"提醒：{reminder.content}",10000)
        QTimer.singleShot(3000,lambda:self.set_state(self.STATE_IDLE))
    def _handle_app_event(self,event):
        if not self.config.get("file_event_animations_enabled",True): return
        anim=self.animation_controller.resolve(event)
        self._state=self.STATE_ALERT if event.category=="reminder" else self.STATE_TALKING
        if anim: self.play_semantic(anim)
    def _open_add_reminder(self):
        d=AddReminderDialog(self)
        if d.exec_(): c,dt=d.values(); self.reminder.add_reminder(c,dt); self._schedule_next_reminder(); self.show_bubble("提醒已保存",4000)
    def _open_reminders(self):
        ReminderListDialog(self.reminder,self).exec_()
        self._schedule_next_reminder()
    def _open_pocket(self):
        from pocket_window import PocketWindow
        if not hasattr(self, "_pocket_window") or self._pocket_window is None:
            self._pocket_window = PocketWindow(
                self.pocket, event_dispatcher=self.events)
        self._pocket_window.refresh()
        self._pocket_window.show()
    def _tray_activated(self,reason):
        if reason==QSystemTrayIcon.DoubleClick: self.show(); self.raise_(); self.show_bubble("Hi! 👋",2500)
        elif reason==QSystemTrayIcon.ActivationReason.Trigger: self._toggle_visibility()
    def _show_context_menu(self,pos):
        m=QMenu(self)
        pa=m.addAction("文件口袋"); aa=m.addAction("新建提醒"); ra=m.addAction("我的提醒"); m.addSeparator()
        sa=m.addAction("设置"); m.addSeparator(); qa=m.addAction("退出")
        act=m.exec_(pos)
        if act==aa: self._open_add_reminder()
        elif act==ra: self._open_reminders()
        elif act==pa: self._open_pocket()
        elif act==sa: self._open_settings()
        elif act==qa: self._quit_app()
    def _open_settings(self):
        d=SettingsDialog(self.config,self)
        if d.exec_(): self._update_from_settings()
    def _update_from_settings(self):
        self.tray_icon.setToolTip(f"{self.config.pet_name} — 桌面助手"); self.character.reload()
        w,h=self.character.base_size(); self._pet_w,self._pet_h=w,h; self.setFixedSize(w+40,h+60)
    def _pil_to_qimage(self,pi):
        if pi.mode!="RGBA": pi=pi.convert("RGBA")
        data=pi.tobytes("raw","RGBA"); from PyQt5.QtGui import QImage
        return QImage(data,pi.width,pi.height,QImage.Format_RGBA8888)
    def _change_scale(self,delta):
        ns=max(1.0,min(6.0,round(float(self.config.get("pet_scale",3))+delta,1)))
        self.config.set("pet_scale",ns); self.character.set_scale(ns)
        w,h=self.character.base_size(); self._pet_w,self._pet_h=w,h; self.setFixedSize(w+40,h+60)
    def _quit_app(self):
        self.file_watch.stop_all(); self._bubble_hide(); self.tray_icon.hide(); QApplication.quit()


def main():
    app=QApplication(sys.argv); app.setApplicationName("Desktop Pet"); app.setQuitOnLastWindowClosed(False)
    app.setFont(theme.font()); app.setStyleSheet(theme.app_qss())
    config=Config(); window=PetWindow(config); window.show()
    if config.get("show_welcome",True):
        QTimer.singleShot(1200,lambda:(
            window.show_bubble("欢迎使用桌面助手\n① 拖文件到角色：临时寄存\n② 单击角色：打开文件口袋\n③ 右键角色：提醒和设置",10000),
            window.set_state(PetWindow.STATE_TALKING),
            QTimer.singleShot(2000,lambda:window.set_state(PetWindow.STATE_IDLE)),
        ))
        config.set("show_welcome",False)
    return app.exec_()
