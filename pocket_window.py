"""Pocket window V2.1 — non-modal floating panel for file management.

V2.1 fixes (per code review):
  * drag-out uses a PocketListWidget subclass that overrides startDrag and
    builds QMimeData + QUrl.fromLocalFile + QDrag (reviewer issue #3).
  * multi-file move updates Pocket refs by SOURCE->DESTINATION mapping, not
    by UUID-vs-filename or by first result (reviewer issue #4).
  * favorites / recents / browse each offer BOTH 复制到 and 移动到, with the
    destination decoupled from the action (reviewer issue #5).
  * Explorer folder shows a refresh button; the snapshot clears when it is
    no longer a valid directory (reviewer issue #2 partial).
"""
from pathlib import Path
from PyQt5.QtCore import Qt, QUrl, QTimer, QPoint, QMimeData
from PyQt5.QtGui import QDesktopServices, QIcon, QDrag
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMenu, QFileDialog, QFrame, QAbstractItemView,
    QApplication,
)
import theme
from file_ops import FileOperationService
from destinations import DestinationService
from explorer import ExplorerService


def _elide(text, max_len=40):
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


class PocketListWidget(QListWidget):
    """QListWidget that exports selected paths as standard local-file URLs."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service

    def _selected_existing_paths(self):
        paths = []
        for li in self.selectedItems():
            item = self.service.get(li.data(Qt.UserRole))
            if item and item.exists:
                paths.append(item.path)
        return paths

    def mime_data_for_selected(self):
        paths = self._selected_existing_paths()
        if not paths:
            return None
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        return mime

    def startDrag(self, supported_actions):
        mime = self.mime_data_for_selected()
        if mime is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)


class PocketWindow(QWidget):
    """Non-modal floating pocket panel (V2.1)."""

    def __init__(self, service, parent=None, file_operations=None,
                 destinations=None, explorer_service=None, event_dispatcher=None):
        super().__init__(parent)
        self.service = service
        self.file_ops = file_operations or FileOperationService()
        self.destinations = destinations or DestinationService()
        self.explorer = explorer_service or ExplorerService()
        self.events = event_dispatcher

        self.setWindowTitle("文件口袋")
        self.setMinimumSize(480, 380)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._explorer_snapshot = None
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast_hide)

        # frameless-window drag support
        self._drag_offset = None

        self._build_ui()
        self.setAcceptDrops(True)
        self.refresh()

    # ── frameless window drag (so the panel can be moved, not stuck) ────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def show_near(self, anchor_rect, screen=None):
        """Open the pocket panel positioned beside the pet (or an anchor)."""
        from PyQt5.QtCore import QRect
        self.adjustSize()
        pw = max(self.sizeHint().width(), self.minimumWidth())
        ph = max(self.sizeHint().height(), self.minimumHeight())
        scr = screen or QApplication.screenAt(anchor_rect.center()) or QApplication.primaryScreen()
        avail = scr.availableGeometry()
        x = anchor_rect.right() + 8
        y = anchor_rect.top()
        if x + pw > avail.right():
            x = anchor_rect.left() - pw - 8
        if y + ph > avail.bottom():
            y = avail.bottom() - ph - 8
        if y < avail.top():
            y = avail.top()
        self.setGeometry(x, y, pw, ph)
        self.show()
        self.raise_()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(6)

        hdr = QHBoxLayout()
        self.title_label = QLabel("文件口袋")
        self.title_label.setObjectName("title")
        self.count_label = QLabel("0 个项目")
        self.count_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        hdr.addWidget(self.title_label); hdr.addStretch(); hdr.addWidget(self.count_label)
        cl.addLayout(hdr)

        # V2.1: dedicated list widget subclass so drag-out actually works.
        self.item_list = PocketListWidget(self.service)
        self.item_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.item_list.setDragEnabled(True)
        self.item_list.setDragDropMode(QAbstractItemView.DragOnly)
        self.item_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._show_context_menu)
        self.item_list.itemSelectionChanged.connect(self._on_selection_changed)
        cl.addWidget(self.item_list, 1)

        self.empty_label = QLabel("拖文件到这里也可以")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px;")
        cl.addWidget(self.empty_label)

        # Explorer section (V2.1: refresh button)
        exp_frame = QFrame()
        exp_frame.setStyleSheet(f"QFrame {{ background: {theme.BG}; border-radius: {theme.RADIUS_SMALL}px; padding: 6px; }}")
        exp_layout = QVBoxLayout(exp_frame)
        exp_layout.setContentsMargins(8, 6, 8, 6)
        exp_layout.setSpacing(4)

        exp_hdr = QHBoxLayout()
        self.explorer_label = QLabel("当前未检测到资源管理器文件夹")
        self.explorer_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;")
        self.explorer_label.setWordWrap(True)
        exp_hdr.addWidget(self.explorer_label, 1)
        self.refresh_explorer_btn = QPushButton("刷新")
        self.refresh_explorer_btn.setObjectName("flat")
        self.refresh_explorer_btn.clicked.connect(self._snapshot_explorer)
        exp_hdr.addWidget(self.refresh_explorer_btn)
        exp_layout.addLayout(exp_hdr)

        btn_row = QHBoxLayout()
        self.copy_explorer_btn = QPushButton("复制到当前文件夹")
        self.copy_explorer_btn.setObjectName("primary")
        self.copy_explorer_btn.setEnabled(False)
        self.copy_explorer_btn.clicked.connect(lambda: self._do_explorer("copy"))
        self.move_explorer_btn = QPushButton("移动到当前文件夹")
        self.move_explorer_btn.setObjectName("primary")
        self.move_explorer_btn.setEnabled(False)
        self.move_explorer_btn.clicked.connect(lambda: self._do_explorer("move"))
        btn_row.addWidget(self.copy_explorer_btn)
        btn_row.addWidget(self.move_explorer_btn)
        exp_layout.addLayout(btn_row)
        cl.addWidget(exp_frame)

        bottom = QHBoxLayout()
        self.dest_btn = QPushButton("选择其他位置...")
        self.dest_btn.clicked.connect(self._show_destination_menu)
        self.more_btn = QPushButton("更多 ⋯")
        self.more_btn.clicked.connect(self._show_more_menu)
        bottom.addWidget(self.dest_btn); bottom.addStretch(); bottom.addWidget(self.more_btn)
        cl.addLayout(bottom)

        root.addWidget(card)

        self._toast_label = QLabel(card)
        self._toast_label.setStyleSheet(f"""
            background: {theme.TOAST_BG}; color: {theme.TOAST_TEXT};
            border-radius: 6px; padding: 6px 14px; font-size: 8pt;
        """)
        self._toast_label.setAlignment(Qt.AlignCenter)
        self._toast_label.hide()

    def show(self):
        self._snapshot_explorer()
        super().show()
        self.raise_()

    def _snapshot_explorer(self):
        d = self.explorer.current_directory()
        self._explorer_snapshot = d if d and d.is_dir() else None
        if self._explorer_snapshot:
            self.explorer_label.setText(f"当前文件夹\n{self._explorer_snapshot}")
        else:
            self.explorer_label.setText("当前未检测到资源管理器文件夹")
        self._on_selection_changed()

    def refresh(self):
        items = self.service.list_items()
        self.count_label.setText(f"{len(items)} 个项目")
        self.empty_label.setVisible(len(items) == 0)
        self.item_list.setVisible(len(items) > 0)
        self.item_list.clear()
        from PyQt5.QtWidgets import QFileIconProvider
        from PyQt5.QtCore import QFileInfo
        provider = QFileIconProvider()
        for item in items:
            li = QListWidgetItem()
            fi = QFileInfo(str(item.path))
            li.setIcon(provider.icon(fi))
            suffix = "" if item.exists else " [missing]"
            li.setText(f"{item.name}{suffix}")
            li.setToolTip(str(item.path))
            li.setData(Qt.UserRole, item.id)
            if not item.exists:
                li.setForeground(Qt.gray)
            self.item_list.addItem(li)
        if self.item_list.count() > 0:
            self.item_list.setCurrentRow(0)
        self._on_selection_changed()

    def _selected_items(self):
        ids = [li.data(Qt.UserRole) for li in self.item_list.selectedItems()]
        return [self.service.get(i) for i in ids if self.service.get(i)]

    def _on_selection_changed(self):
        has = len(self._selected_items()) > 0
        can_explorer = has and self._explorer_snapshot is not None
        self.copy_explorer_btn.setEnabled(can_explorer)
        self.move_explorer_btn.setEnabled(can_explorer)

    def _toast(self, text, ms=3000):
        self._toast_label.setText(text)
        self._toast_label.adjustSize()
        card = self.findChild(QFrame)
        if card:
            self._toast_label.move(card.width() // 2 - self._toast_label.width() // 2,
                                   card.height() - self._toast_label.height() - 8)
        self._toast_label.show()
        self._toast_timer.start(ms)

    def _toast_hide(self):
        self._toast_label.hide()

    # ── core file operation with source->destination mapping ───────────────
    def _run_operation(self, action, dest, sources_desc=None):
        """Execute copy/move, update Pocket refs by source->destination."""
        sel = self._selected_items()
        if not sel:
            return None
        sources = [p.path for p in sel]
        # resolve destination strictly
        dest = Path(dest).expanduser().resolve()
        if not dest.is_dir():
            self._toast("目标文件夹不存在")
            return None
        report = self.file_ops.copy(sources, dest) if action == "copy" else self.file_ops.move(sources, dest)
        if report.succeeded:
            self.destinations.record_recent(dest)
            # V2.1: map each succeeded item by source path -> destination path
            if action == "move":
                src_to_dst = {r.source: r.destination for r in report.items if r.status == "succeeded"}
                for item in sel:
                    dst = src_to_dst.get(item.path)
                    if dst is not None:
                        self.service.replace_path(item.id, dst)
            verb = "已复制" if action == "copy" else "已移动"
            self._toast(f"{verb}到 {dest}")
            if self.events:
                from events import AppEvent
                self.events.dispatch(AppEvent("file_operation", action, report))
            self.refresh()
            return report
        else:
            self._toast(f"操作失败: {report.items[0].error if report.items else '未知错误'}")
            return None

    def _do_explorer(self, action):
        if not self._explorer_snapshot:
            self._toast("当前未检测到资源管理器文件夹")
            return None
        return self._run_operation(action, self._explorer_snapshot)

    def _show_destination_menu(self):
        menu = QMenu(self)
        sel = self._selected_items()
        if not sel:
            menu.addAction("请先选择文件").setEnabled(False)
            menu.exec_(self.dest_btn.mapToGlobal(QPoint(0, self.dest_btn.height())))
            return

        # Current Explorer — both actions, keep same as main buttons.
        if self._explorer_snapshot:
            esc = _elide(str(self._explorer_snapshot), 28)
            menu.addAction(f"复制到当前文件夹  {esc}").triggered.connect(lambda: self._do_explorer("copy"))
            menu.addAction(f"移动到当前文件夹  {esc}").triggered.connect(lambda: self._do_explorer("move"))
            menu.addSeparator()

        # Favorites + Recents: decouple destination from action.
        for fav in self.destinations.list_favorites()[:5]:
            nm = f"常用  {_elide(fav.name, 24)}"
            menu.addAction(f"{nm}  [复制]").triggered.connect(lambda checked, p=fav.path: self._run_operation("copy", p))
            menu.addAction(f"{nm}  [移动]").triggered.connect(lambda checked, p=fav.path: self._run_operation("move", p))
        if self.destinations.list_favorites():
            menu.addSeparator()

        for rec in self.destinations.list_recents()[:3]:
            nm = f"最近  {_elide(rec.name, 24)}"
            menu.addAction(f"{nm}  [复制]").triggered.connect(lambda checked, p=rec.path: self._run_operation("copy", p))
            menu.addAction(f"{nm}  [移动]").triggered.connect(lambda checked, p=rec.path: self._run_operation("move", p))
        if self.destinations.list_recents():
            menu.addSeparator()

        browse = menu.addAction("浏览其他文件夹...")
        browse.triggered.connect(self._browse_other)
        menu.exec_(self.dest_btn.mapToGlobal(QPoint(0, self.dest_btn.height())))

    def _browse_other(self):
        menu = QMenu(self)
        menu.addAction("复制到...").triggered.connect(lambda: self._browse_action("copy"))
        menu.addAction("移动到...").triggered.connect(lambda: self._browse_action("move"))
        menu.exec_(self.dest_btn.mapToGlobal(QPoint(0, self.dest_btn.height())))

    def _browse_action(self, action):
        dest = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if dest:
            self._run_operation(action, Path(dest))

    def _show_more_menu(self):
        menu = QMenu(self)
        sel = self._selected_items()
        if not sel:
            menu.addAction("请先选择文件").setEnabled(False)
            menu.exec_(self.more_btn.mapToGlobal(QPoint(0, self.more_btn.height())))
            return
        if len(sel) == 1:
            menu.addAction("打开").triggered.connect(self._open_selected)
            menu.addAction("在资源管理器中显示").triggered.connect(self._reveal_selected)
            menu.addAction("复制路径").triggered.connect(self._copy_path)
            menu.addSeparator()
        menu.addAction(f"从口袋移除 ({len(sel)})").triggered.connect(self._remove_selected)
        menu.exec_(self.more_btn.mapToGlobal(QPoint(0, self.more_btn.height())))

    def _open_selected(self):
        sel = self._selected_items()
        if sel and sel[0].exists:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(sel[0].path)))

    def _reveal_selected(self):
        import subprocess
        sel = self._selected_items()
        if sel and sel[0].exists:
            subprocess.Popen(["explorer.exe", "/select,", str(sel[0].path)],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def _copy_path(self):
        sel = self._selected_items()
        if sel:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText("\n".join(str(s.path) for s in sel))
            self._toast("路径已复制")

    def _remove_selected(self):
        for item in self._selected_items():
            self.service.remove(item.id)
        self.refresh()

    def _show_context_menu(self, pos):
        li = self.item_list.itemAt(pos)
        if not li:
            return
        item = self.service.get(li.data(Qt.UserRole))
        if not item:
            return
        menu = QMenu(self)
        menu.addAction("打开").triggered.connect(self._open_selected)
        menu.addAction("在资源管理器中显示").triggered.connect(self._reveal_selected)
        menu.addAction("复制路径").triggered.connect(self._copy_path)
        menu.addSeparator()
        menu.addAction("从口袋移除").triggered.connect(self._remove_selected)
        menu.exec_(self.item_list.mapToGlobal(pos))

    # ── Drag & drop ─────────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        added = 0
        for url in event.mimeData().urls():
            if url.isLocalFile():
                try:
                    self.service.add(Path(url.toLocalFile()))
                    added += 1
                except (OSError, ValueError):
                    continue
        if added:
            self._toast(f"已添加 {added} 个项目")
            self.refresh()
        event.acceptProposedAction()

    def closeEvent(self, event):
        self.hide()
        event.ignore()
