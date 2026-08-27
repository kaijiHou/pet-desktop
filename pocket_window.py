"""Pocket window V2 — non-modal floating panel for file management.

Features:
  - Non-modal (show/hide, not exec_)
  - Multi-select (Ctrl+click, Shift+click)
  - Primary: 复制到当前文件夹 / 移动到当前文件夹
  - Destination picker: 当前文件夹 + favorites + recents + browse
  - QFileIconProvider for system icons
  - Elided paths (full in tooltip)
  - Toast for success (not QMessageBox)
  - Drag-in to add, drag-out with standard QDrag
  - Explorer directory snapshot on open
"""
from pathlib import Path
from PyQt5.QtCore import Qt, QUrl, QTimer, QPoint, QMimeData
from PyQt5.QtGui import QDesktopServices, QIcon, QDrag
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMenu, QFileDialog, QFrame, QSizePolicy, QMessageBox,
    QAbstractItemView,
)
import theme
from file_ops import FileOperationService
from destinations import DestinationService
from explorer import ExplorerService


def _elide(text, max_len=40):
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


class PocketWindow(QWidget):
    """Non-modal floating pocket panel (V2)."""

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

        self._explorer_snapshot = None  # captured on open
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lambda: self._toast_label.hide())

        self._build_ui()
        self.setAcceptDrops(True)
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        self.title_label = QLabel("文件口袋")
        self.title_label.setObjectName("title")
        self.count_label = QLabel("0 个项目")
        self.count_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        hdr.addWidget(self.title_label); hdr.addStretch(); hdr.addWidget(self.count_label)
        cl.addLayout(hdr)

        # List
        self.item_list = QListWidget()
        self.item_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.item_list.setDragEnabled(True)
        self.item_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._show_context_menu)
        self.item_list.itemSelectionChanged.connect(self._on_selection_changed)
        cl.addWidget(self.item_list, 1)

        self.empty_label = QLabel("拖文件到这里也可以")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px;")
        cl.addWidget(self.empty_label)

        # Explorer section
        exp_frame = QFrame()
        exp_frame.setStyleSheet(f"QFrame {{ background: {theme.BG}; border-radius: {theme.RADIUS_SMALL}px; padding: 6px; }}")
        exp_layout = QVBoxLayout(exp_frame)
        exp_layout.setContentsMargins(8, 6, 8, 6)
        exp_layout.setSpacing(4)

        self.explorer_label = QLabel("当前未检测到资源管理器文件夹")
        self.explorer_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 8pt;")
        exp_layout.addWidget(self.explorer_label)

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

        # Bottom buttons
        bottom = QHBoxLayout()
        self.dest_btn = QPushButton("选择其他位置...")
        self.dest_btn.clicked.connect(self._show_destination_menu)
        self.more_btn = QPushButton("更多 ⋯")
        self.more_btn.clicked.connect(self._show_more_menu)
        bottom.addWidget(self.dest_btn); bottom.addStretch(); bottom.addWidget(self.more_btn)
        cl.addLayout(bottom)

        root.addWidget(card)

        # Toast
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
        self._explorer_snapshot = d
        if d:
            self.explorer_label.setText(f"当前文件夹\n{d}")
            self.copy_explorer_btn.setEnabled(True)
            self.move_explorer_btn.setEnabled(True)
        else:
            self.explorer_label.setText("当前未检测到资源管理器文件夹")
            self.copy_explorer_btn.setEnabled(False)
            self.move_explorer_btn.setEnabled(False)

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
            icon = provider.icon(fi)
            suffix = "" if item.exists else " [missing]"
            li.setIcon(icon)
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
        sel = self._selected_items()
        has = len(sel) > 0
        self.copy_explorer_btn.setEnabled(has and self._explorer_snapshot is not None)
        self.move_explorer_btn.setEnabled(has and self._explorer_snapshot is not None)

    def _toast(self, text, ms=3000):
        self._toast_label.setText(text)
        self._toast_label.adjustSize()
        card = self.findChild(QFrame)
        if card:
            self._toast_label.move(card.width() // 2 - self._toast_label.width() // 2,
                                   card.height() - self._toast_label.height() - 8)
        self._toast_label.show()
        self._toast_timer.start(ms)

    def _do_explorer(self, action):
        dest = self._explorer_snapshot
        if not dest: return
        sel = self._selected_items()
        if not sel: return
        sources = [p.path for p in sel]
        report = self.file_ops.copy(sources, dest) if action == "copy" else self.file_ops.move(sources, dest)
        if report.succeeded:
            self.destinations.record_recent(dest)
            self._toast(f"{'已复制' if action == 'copy' else '已移动'}到 {dest}")
            if self.events:
                from events import AppEvent
                self.events.dispatch(AppEvent("file_operation", action, report))
            if action == "move":
                for item in sel:
                    if item.id in [r.source.name for r in report.items if r.status == "succeeded"]:
                        self.service.replace_path(item.id, report.items[0].destination)
            self.refresh()
        else:
            self._toast(f"操作失败: {report.items[0].error if report.items else '未知错误'}")

    def _show_destination_menu(self):
        menu = QMenu(self)
        sel = self._selected_items()
        if not sel:
            menu.addAction("请先选择文件").setEnabled(False)
            menu.exec_(self.dest_btn.mapToGlobal(QPoint(0, self.dest_btn.height())))
            return

        # Current Explorer
        if self._explorer_snapshot:
            act = menu.addAction(f"当前文件夹  {_elide(str(self._explorer_snapshot), 30)}")
            act.triggered.connect(lambda: self._do_explorer("copy"))
            act = menu.addAction(f"移动到当前文件夹  {_elide(str(self._explorer_snapshot), 30)}")
            act.triggered.connect(lambda: self._do_explorer("move"))
            menu.addSeparator()

        # Favorites
        favs = self.destinations.list_favorites()
        if favs:
            for fav in favs[:5]:
                act = menu.addAction(f"常用  {_elide(fav.name, 25)}")
                act.triggered.connect(lambda checked, p=fav.path: self._do_copy_move(p, "copy"))
            menu.addSeparator()

        # Recents
        recs = self.destinations.list_recents()
        if recs:
            for rec in recs[:3]:
                act = menu.addAction(f"最近  {_elide(rec.name, 25)}")
                act.triggered.connect(lambda checked, p=rec.path: self._do_copy_move(p, "copy"))
            menu.addSeparator()

        browse = menu.addAction("浏览其他文件夹...")
        browse.triggered.connect(self._browse_copy)
        menu.exec_(self.dest_btn.mapToGlobal(QPoint(0, self.dest_btn.height())))

    def _do_copy_move(self, dest, action):
        sel = self._selected_items()
        if not sel: return
        sources = [p.path for p in sel]
        report = self.file_ops.copy(sources, dest) if action == "copy" else self.file_ops.move(sources, dest)
        if report.succeeded:
            self.destinations.record_recent(dest)
            self._toast(f"已复制到 {dest}")
            self.refresh()
        else:
            self._toast(f"操作失败")

    def _browse_copy(self):
        dest = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if dest: self._do_copy_move(Path(dest), "copy")

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
        if not li: return
        item = self.service.get(li.data(Qt.UserRole))
        if not item: return
        menu = QMenu(self)
        menu.addAction("打开").triggered.connect(self._open_selected)
        menu.addAction("在资源管理器中显示").triggered.connect(self._reveal_selected)
        menu.addAction("复制路径").triggered.connect(self._copy_path)
        menu.addSeparator()
        menu.addAction("从口袋移除").triggered.connect(self._remove_selected)
        menu.exec_(self.item_list.mapToGlobal(pos))

    # ── Drag & drop ──

    def startDrag(self, supported_actions):
        sel = self._selected_items()
        urls = [QUrl.fromLocalFile(str(s.path)) for s in sel if s.exists]
        if not urls: return
        mime = QMimeData(); mime.setUrls(urls)
        drag = QDrag(self); drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)

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
