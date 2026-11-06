"""Main application window."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStyle,
    QToolButton,
    QToolTip,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import APP_NAME, AUTHOR, COPYRIGHT, __version__
from app.drive_manager import Drive, list_drives, usage_for
from app.export_manager import export_csv, export_json
from app.file_categories import CATEGORIES, color_of
from app.localization import Translator
from app.paths import resource_path
from app.scanner import Node, ScanStats, largest_files, largest_folders, search
from app.settings import Settings
from app.widgets.common import (
    COLOR_ROLE,
    SIZE_FRACTION_ROLE,
    DonutWidget,
    DriveCard,
    ElidedLabel,
    SizeBarDelegate,
)
from app.widgets.treemap_widget import TreemapWidget
from app.workers import ScanWorker

NODE_ROLE = int(Qt.ItemDataRole.UserRole)
SORT_ROLE = int(Qt.ItemDataRole.UserRole) + 3
MAX_LIST_ROWS = 3000


class _NodeItem(QTreeWidgetItem):
    """Tree row that sorts by the typed key stored in SORT_ROLE (not by display text)."""

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        tree = self.treeWidget()
        col = tree.sortColumn() if tree is not None else 0
        a, b = self.data(col, SORT_ROLE), other.data(col, SORT_ROLE)
        try:
            return bool(a < b)
        except TypeError:
            return False


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(8)
    return frame, lay


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None, *, persist_settings: bool = True) -> None:
        super().__init__()
        self.settings = settings or Settings()
        self._persist = persist_settings
        self.tr_ = Translator(self.settings.language)

        self.drives: list[Drive] = []
        self.selected_path: str = ""
        self.root: Node | None = None
        self.current: Node | None = None
        self.stats: ScanStats | None = None
        self.worker: ScanWorker | None = None
        self._scan_started = 0.0
        self._scan_status = "status_idle"
        self._scan_drive_used = 0
        self._cat_labels: dict[str, tuple[QLabel, QLabel, QLabel]] = {}

        self.setMinimumSize(1000, 640)
        self.resize(1360, 820)
        icon_path = resource_path("assets", "icon.png")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(250)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._refresh_list)

        self.refresh_drives()
        self.retranslate()

    # ================================================================= UI
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_center(), 1)
        body.addWidget(self._build_right_panel())
        outer.addLayout(body, 1)
        outer.addWidget(self._build_statusbar())

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(10)
        self.brand = QLabel(APP_NAME)
        self.brand.setObjectName("brand")
        self.version_chip = QLabel(f"v{__version__}")
        self.version_chip.setObjectName("chip")
        self.drive_chip = ElidedLabel()
        self.drive_chip.setObjectName("chip")
        self.drive_chip.setMinimumWidth(260)
        self.drive_chip.setMaximumWidth(420)
        self.status_chip = QLabel()
        self.status_chip.setObjectName("chip")
        self.lang_btn = QPushButton()
        self.lang_btn.clicked.connect(self._toggle_language)
        self.settings_btn = QToolButton()
        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu = QMenu(self)
        self.act_csv = QAction(self)
        self.act_csv.triggered.connect(lambda: self._export("csv"))
        self.act_json = QAction(self)
        self.act_json.triggered.connect(lambda: self._export("json"))
        self.lang_menu = QMenu(self)
        self.lang_group = QActionGroup(self)
        self.act_fa = QAction(self, checkable=True)
        self.act_en = QAction(self, checkable=True)
        for act, code in ((self.act_fa, "fa"), (self.act_en, "en")):
            self.lang_group.addAction(act)
            self.lang_menu.addAction(act)
            act.triggered.connect(lambda _=False, c=code: self.set_language(c))
        self.act_about = QAction(self)
        self.act_about.triggered.connect(self._show_about)
        self.menu.addAction(self.act_csv)
        self.menu.addAction(self.act_json)
        self.menu.addSeparator()
        self.menu.addMenu(self.lang_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.act_about)
        self.settings_btn.setMenu(self.menu)

        for w in (self.brand, self.version_chip, self.drive_chip):
            lay.addWidget(w)
        lay.addStretch(1)
        lay.addWidget(self.status_chip)
        lay.addWidget(self.lang_btn)
        lay.addWidget(self.settings_btn)
        return header

    def _build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(340)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.drives_label = QLabel()
        self.drives_label.setObjectName("section")
        self.drive_list = QListWidget()
        self.drive_list.setMaximumHeight(190)
        self.drive_list.currentItemChanged.connect(self._on_drive_selected)
        self.drive_list.itemDoubleClicked.connect(lambda _i: self.start_scan())

        row = QHBoxLayout()
        self.scan_btn = QPushButton()
        self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(lambda: self.start_scan())
        self.folder_btn = QPushButton()
        self.folder_btn.clicked.connect(self._choose_folder)
        row.addWidget(self.scan_btn, 1)
        row.addWidget(self.folder_btn, 1)

        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(lambda _t: self._search_timer.start())
        self.filter_combo = QComboBox()
        self.filter_combo.currentIndexChanged.connect(lambda _i: self._refresh_list())

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSortingEnabled(True)
        self.tree.setItemDelegateForColumn(2, SizeBarDelegate(self.tree))
        self.tree.itemDoubleClicked.connect(self._on_tree_double_click)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        header.resizeSection(2, 120)

        lay.addWidget(self.drives_label)
        lay.addWidget(self.drive_list)
        lay.addLayout(row)
        lay.addWidget(self.search_edit)
        lay.addWidget(self.filter_combo)
        lay.addWidget(self.tree, 1)
        return side

    def _build_center(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        nav = QHBoxLayout()
        self.up_btn = QPushButton()
        self.up_btn.clicked.connect(self._go_up)
        self.path_label = ElidedLabel()
        self.path_label.setObjectName("muted")
        nav.addWidget(self.up_btn)
        nav.addWidget(self.path_label, 1)
        self.treemap = TreemapWidget()
        self.treemap.navigate_requested.connect(self.navigate)
        self.treemap.hovered.connect(self._on_hover)
        lay.addLayout(nav)
        lay.addWidget(self.treemap, 1)
        return wrap

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightpanel")
        panel.setFixedWidth(320)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # --- storage card
        card, cl = _card()
        self.stats_title = QLabel()
        self.stats_title.setObjectName("section")
        self.usage_bar = QProgressBar()
        self.usage_bar.setRange(0, 100)
        self.usage_bar.setTextVisible(False)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self.stat_keys: dict[str, QLabel] = {}
        self.stat_vals: dict[str, QLabel] = {}
        for i, key in enumerate(("capacity", "used", "free", "files", "folders")):
            k, v = QLabel(), QLabel()
            k.setObjectName("muted")
            v.setObjectName("value")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(k, i, 0)
            grid.addWidget(v, i, 1)
            self.stat_keys[key], self.stat_vals[key] = k, v
        for w in (self.stats_title, self.usage_bar):
            cl.addWidget(w)
        cl.addLayout(grid)
        lay.addWidget(card)

        # --- categories card
        card, cl = _card()
        self.cat_title = QLabel()
        self.cat_title.setObjectName("section")
        self.donut = DonutWidget()
        self.donut.setFixedHeight(130)
        cl.addWidget(self.cat_title)
        cl.addWidget(self.donut)
        cat_grid = QGridLayout()
        cat_grid.setHorizontalSpacing(8)
        cat_grid.setColumnStretch(1, 1)
        for i, cat in enumerate(CATEGORIES):
            sw = QLabel()
            sw.setFixedSize(12, 12)
            sw.setStyleSheet(f"background:{color_of(cat)}; border-radius:3px;")
            name, val = QLabel(), QLabel()
            val.setObjectName("muted")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cat_grid.addWidget(sw, i, 0)
            cat_grid.addWidget(name, i, 1)
            cat_grid.addWidget(val, i, 2)
            self._cat_labels[cat] = (sw, name, val)
        cl.addLayout(cat_grid)
        lay.addWidget(card)

        # --- largest files / folders
        card, cl = _card()
        self.big_files_title = QLabel()
        self.big_files_title.setObjectName("section")
        self.big_files = QListWidget()
        self.big_files.setFixedHeight(170)
        self.big_files.itemDoubleClicked.connect(self._on_big_item)
        cl.addWidget(self.big_files_title)
        cl.addWidget(self.big_files)
        lay.addWidget(card)

        card, cl = _card()
        self.big_dirs_title = QLabel()
        self.big_dirs_title.setObjectName("section")
        self.big_dirs = QListWidget()
        self.big_dirs.setFixedHeight(170)
        self.big_dirs.itemDoubleClicked.connect(self._on_big_item)
        cl.addWidget(self.big_dirs_title)
        cl.addWidget(self.big_dirs)
        lay.addWidget(card)

        card, cl = _card()
        self.issues_title = QLabel()
        self.issues_title.setObjectName("section")
        self.issues_text = QLabel()
        self.issues_text.setObjectName("muted")
        self.issues_text.setWordWrap(True)
        cl.addWidget(self.issues_title)
        cl.addWidget(self.issues_text)
        lay.addWidget(card)

        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return panel

    def _build_statusbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("statusbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(16)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(220)
        self.st_files = QLabel()
        self.st_dirs = QLabel()
        self.st_elapsed = QLabel()
        self.st_current = ElidedLabel()
        self.st_current.setObjectName("muted")
        self.cancel_btn = QPushButton()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_scan)
        self.copyright_label = QLabel(COPYRIGHT)
        self.copyright_label.setObjectName("muted")
        for w in (self.progress, self.st_files, self.st_dirs, self.st_elapsed):
            lay.addWidget(w)
        lay.addWidget(self.st_current, 1)
        lay.addWidget(self.cancel_btn)
        lay.addWidget(self.copyright_label)
        return bar

    # ============================================================ language
    def set_language(self, code: str) -> None:
        self.tr_.set_language(code)
        self.settings.language = self.tr_.language
        if self._persist:
            self.settings.save()
        self.retranslate()

    def _toggle_language(self) -> None:
        self.set_language("en" if self.tr_.language == "fa" else "fa")

    def retranslate(self) -> None:
        t = self.tr_
        app = QApplication.instance()
        direction = Qt.LayoutDirection.RightToLeft if t.is_rtl else Qt.LayoutDirection.LeftToRight
        if isinstance(app, QApplication):
            app.setLayoutDirection(direction)
        self.setLayoutDirection(direction)
        self.setWindowTitle(f"{t.t('window_title')} {__version__}")

        self.lang_btn.setText(t.t("switch_language"))
        self.settings_btn.setText(t.t("settings"))
        self.act_csv.setText(t.t("export_csv"))
        self.act_json.setText(t.t("export_json"))
        self.lang_menu.setTitle(t.t("language"))
        self.act_fa.setText(t.t("lang_fa"))
        self.act_en.setText(t.t("lang_en"))
        self.act_fa.setChecked(t.language == "fa")
        self.act_en.setChecked(t.language == "en")
        self.act_about.setText(t.t("about"))

        self.drives_label.setText(t.t("drives"))
        self.scan_btn.setText(t.t("scan"))
        self.folder_btn.setText(t.t("choose_folder"))
        self.search_edit.setPlaceholderText(t.t("search_placeholder"))
        self.tree.setHeaderLabels([t.t("col_name"), t.t("col_type"), t.t("col_size")])
        self.up_btn.setText("↑ " + t.t("up"))
        self.cancel_btn.setText(t.t("cancel"))

        self.stats_title.setText(t.t("stats_title"))
        for key in self.stat_keys:
            self.stat_keys[key].setText(t.t(key))
        self.cat_title.setText(t.t("categories"))
        for cat, (_sw, name, _val) in self._cat_labels.items():
            name.setText(t.t(f"cat_{cat}"))
        self.big_files_title.setText(t.t("largest_files"))
        self.big_dirs_title.setText(t.t("largest_folders"))
        self.big_dirs_title.setToolTip(t.t("largest_folders_tip"))
        self.issues_title.setText(t.t("issues"))

        self.treemap.set_formatter(t.size)
        self.treemap.set_placeholder(t.t("empty_scanning") if self.worker else t.t("empty_state"))

        self.filter_combo.blockSignals(True)
        selected = self.filter_combo.currentData()
        self.filter_combo.clear()
        self.filter_combo.addItem(t.t("filter_all"), None)
        for cat in CATEGORIES:
            self.filter_combo.addItem(t.t(f"cat_{cat}"), cat)
        idx = self.filter_combo.findData(selected)
        self.filter_combo.setCurrentIndex(max(0, idx))
        self.filter_combo.blockSignals(False)

        self._populate_drive_list()
        self._update_header()
        self._update_status_labels()
        self._update_stats_panel()
        self._update_nav()
        self._refresh_list()
        self._refresh_big_lists()

    # =============================================================== drives
    def refresh_drives(self) -> None:
        self.drives = list_drives()
        self._populate_drive_list()

    def _populate_drive_list(self) -> None:
        t = self.tr_
        keep = self.selected_path
        self.drive_list.blockSignals(True)
        self.drive_list.clear()
        select_row = -1
        for i, d in enumerate(self.drives):
            title = t.t("home_folder") if d.is_home else d.name
            if d.fstype and not d.is_home:
                title += f"  ·  {d.fstype}"
            caption = f"{t.size(d.free)} / {t.size(d.total)}  ·  {t.t('free')}"
            item = QListWidgetItem()
            item.setData(NODE_ROLE, d.path)
            card = DriveCard(title, caption, d.percent)
            item.setSizeHint(card.sizeHint())
            self.drive_list.addItem(item)
            self.drive_list.setItemWidget(item, card)
            if keep and d.path == keep:
                select_row = i
        if keep and select_row < 0:
            self.drive_list.setCurrentRow(-1)  # custom folder: no drive highlighted
        elif self.drive_list.count():
            self.drive_list.setCurrentRow(max(0, select_row))
            if not keep:
                self.selected_path = self.drives[0].path
        self.drive_list.blockSignals(False)
        self._update_header()
        self._update_stats_panel()

    def _on_drive_selected(self, item: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if item is None:
            return
        if self.worker is None:
            self.selected_path = str(item.data(NODE_ROLE))
        self._update_header()
        self._update_stats_panel()

    def _choose_folder(self) -> None:
        start = self.settings.last_folder or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, self.tr_.t("dialog_choose_folder"), start)
        if path:
            self.settings.last_folder = path
            if self._persist:
                self.settings.save()
            self.start_scan(path)

    # ================================================================ scan
    def start_scan(self, path: str | None = None) -> None:
        t = self.tr_
        if self.worker is not None:
            QMessageBox.information(self, t.t("info_title"), t.t("scan_busy"))
            return
        target = path or self.selected_path
        if not target:
            return
        if not Path(target).is_dir():
            QMessageBox.warning(self, t.t("error_title"), t.t("path_missing", path=target))
            return

        self.selected_path = target
        self._scan_drive_used = 0
        for d in self.drives:
            if d.path == target:
                self._scan_drive_used = d.used
        self.root = self.current = None
        self.stats = None
        self.treemap.set_root(None)
        self.worker = ScanWorker(target, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.failed.connect(self._on_failed)
        self._scan_started = time.monotonic()
        self._set_scanning(True)
        self.worker.start()
        self.retranslate()

    def _set_scanning(self, scanning: bool) -> None:
        self.scan_btn.setEnabled(not scanning)
        self.folder_btn.setEnabled(not scanning)
        self.cancel_btn.setEnabled(scanning)
        self.drive_list.setEnabled(not scanning)
        if scanning:
            self._scan_status = "status_scanning"
            self._elapsed_timer.start()
            if self._scan_drive_used > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(0)
            else:
                self.progress.setRange(0, 0)  # busy indicator
        else:
            self._elapsed_timer.stop()
            self.progress.setRange(0, 100)

    def _cancel_scan(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, files: int, dirs: int, nbytes: int, path: str) -> None:
        t = self.tr_
        self.st_files.setText(t.t("status_files", n=t.number(files)))
        self.st_dirs.setText(t.t("status_folders", n=t.number(dirs)))
        self.st_current.setFullText(t.t("status_current", p=path))
        if self._scan_drive_used > 0:
            self.progress.setValue(min(99, int(nbytes * 100 / self._scan_drive_used)))

    def _finish_worker(self) -> None:
        worker, self.worker = self.worker, None
        if worker is not None:
            worker.shutdown()
            worker.deleteLater()
        self._set_scanning(False)

    def _on_finished(self, root: Node, stats: ScanStats) -> None:
        self._finish_worker()
        self.show_result(root, stats)

    def show_result(self, root: Node, stats: ScanStats) -> None:
        self.root = self.current = root
        self.stats = stats
        self._scan_status = "status_done"
        self.progress.setValue(100)
        self.treemap.set_root(root, animate=True)
        self.retranslate()

    def _on_cancelled(self) -> None:
        self._finish_worker()
        self._scan_status = "status_cancelled"
        self.progress.setValue(0)
        self.retranslate()

    def _on_failed(self, message: str) -> None:
        self._finish_worker()
        self._scan_status = "status_error"
        self.retranslate()
        QMessageBox.critical(self, self.tr_.t("error_title"), self.tr_.t("scan_failed", error=message))

    def _tick_elapsed(self) -> None:
        self._update_status_labels()

    # ========================================================== navigation
    def navigate(self, node: Node) -> None:
        if node is None or not node.is_dir or node is self.current:
            return
        self.current = node
        self.treemap.set_root(node, animate=True)
        self._update_nav()
        self._refresh_list()
        self._refresh_big_lists()

    def _go_up(self) -> None:
        if self.current is not None and self.current.parent is not None:
            self.navigate(self.current.parent)

    def _update_nav(self) -> None:
        self.up_btn.setEnabled(bool(self.current and self.current.parent))
        self.path_label.setFullText(self.current.path if self.current else "")

    def _on_hover(self, node: Node | None, pos: QPoint | None) -> None:
        if node is None or pos is None or self.current is None:
            QToolTip.hideText()
            return
        t = self.tr_
        frac = node.size / self.current.size if self.current.size else 0.0
        if node.is_dir:
            kind = t.t("type_folder")
        elif node.is_aggregate:
            kind = t.t("type_more_files", n=t.number(node.files))
        else:
            kind = t.t(f"cat_{node.category}")
        name = node.name if not node.is_aggregate else "…"
        text = t.t("hover_info", name=name, size=t.size(node.size), pct=t.percent(frac), kind=kind)
        QToolTip.showText(pos, text.replace("&", "&amp;").replace("<", "&lt;"), self.treemap)

    # ============================================================== lists
    def _type_text(self, node: Node) -> str:
        t = self.tr_
        if node.is_dir:
            return t.t("type_folder")
        if node.is_aggregate:
            return t.t("type_more_files", n=t.number(node.files))
        return t.t(f"cat_{node.category}")

    def _refresh_list(self) -> None:
        tree = self.tree
        tree.setSortingEnabled(False)
        tree.clear()
        if self.current is None:
            tree.setSortingEnabled(True)
            return
        text = self.search_edit.text().strip()
        cat = self.filter_combo.currentData()
        if text or cat:
            nodes = search(self.current, text, cat, limit=MAX_LIST_ROWS)
        else:
            nodes = self.current.children[:MAX_LIST_ROWS]
        total = self.current.size or 1
        style = self.style()
        dir_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        for node in nodes:
            name = node.name if not node.is_aggregate else self.tr_.t("type_more_files", n=self.tr_.number(node.files))
            item = _NodeItem([name, self._type_text(node), self.tr_.size(node.size)])
            item.setIcon(0, dir_icon if node.is_dir else file_icon)
            item.setData(0, NODE_ROLE, node)
            item.setData(0, SORT_ROLE, (not node.is_dir, node.name.casefold()))
            item.setData(1, SORT_ROLE, (node.is_dir, node.category))
            item.setData(2, SORT_ROLE, node.size)
            item.setData(2, SIZE_FRACTION_ROLE, node.size / total)
            item.setData(2, COLOR_ROLE, color_of(node.category))
            item.setToolTip(0, node.path)
            tree.addTopLevelItem(item)
        tree.setSortingEnabled(True)
        tree.sortByColumn(2, Qt.SortOrder.DescendingOrder)

    def _on_tree_double_click(self, item: QTreeWidgetItem, _col: int) -> None:
        node = item.data(0, NODE_ROLE)
        if isinstance(node, Node):
            self.navigate(node if node.is_dir else (node.parent or node))

    def _refresh_big_lists(self) -> None:
        t = self.tr_
        self.big_files.clear()
        self.big_dirs.clear()
        if self.current is None:
            return
        for lst, nodes, size_of in (
            (self.big_files, largest_files(self.current, 8), lambda n: n.size),
            (self.big_dirs, largest_folders(self.current, 8), lambda n: n.own_size),
        ):
            for node in nodes:
                item = QListWidgetItem(f"{node.name}\n{t.size(size_of(node))}")
                item.setData(NODE_ROLE, node)
                item.setToolTip(node.path)
                lst.addItem(item)

    def _on_big_item(self, item: QListWidgetItem) -> None:
        node = item.data(NODE_ROLE)
        if isinstance(node, Node):
            self.navigate(node if node.is_dir else (node.parent or node))

    # ============================================================== labels
    def _update_header(self) -> None:
        t = self.tr_
        self.drive_chip.setFullText(self.selected_path or t.t("no_drive"))
        self.status_chip.setText(t.t(self._scan_status))

    def _update_status_labels(self) -> None:
        t = self.tr_
        self.status_chip.setText(t.t(self._scan_status))
        if self.worker is not None:
            self.st_elapsed.setText(t.t("status_elapsed", t=t.duration(time.monotonic() - self._scan_started)))
            return
        files = self.stats.files if self.stats else 0
        dirs = self.stats.dirs if self.stats else 0
        elapsed = self.stats.elapsed if self.stats else 0.0
        self.st_files.setText(t.t("status_files", n=t.number(files)))
        self.st_dirs.setText(t.t("status_folders", n=t.number(dirs)))
        self.st_elapsed.setText(t.t("status_elapsed", t=t.duration(elapsed)))
        self.st_current.setFullText("")

    def _update_stats_panel(self) -> None:
        t = self.tr_
        total, used, free = usage_for(self.selected_path) if self.selected_path else (0, 0, 0)
        self.stat_vals["capacity"].setText(t.size(total))
        self.stat_vals["used"].setText(t.size(used))
        self.stat_vals["free"].setText(t.size(free))
        self.usage_bar.setValue(int(used * 100 / total) if total else 0)
        st = self.stats
        self.stat_vals["files"].setText(t.number(st.files) if st else "—")
        self.stat_vals["folders"].setText(t.number(st.dirs) if st else "—")

        slices: list[tuple[str, float]] = []
        scanned = sum(st.cat_sizes.values()) if st else 0
        for cat, (_sw, _name, val) in self._cat_labels.items():
            size = st.cat_sizes.get(cat, 0) if st else 0
            val.setText(f"{t.size(size)} · {t.percent(size / scanned)}" if scanned and size else "—")
            slices.append((color_of(cat), float(size)))
        self.donut.set_data(slices, t.percent(used / total) if total else "")
        if st:
            self.issues_text.setText(t.t("issues_text", errors=t.number(st.error_count), links=t.number(st.skipped_links)))
        else:
            self.issues_text.setText("—")

    # ============================================================== dialogs
    def _export(self, kind: str) -> None:
        t = self.tr_
        if self.root is None:
            QMessageBox.information(self, t.t("info_title"), t.t("no_data"))
            return
        title = t.t("dialog_export_csv" if kind == "csv" else "dialog_export_json")
        flt = "CSV (*.csv)" if kind == "csv" else "JSON (*.json)"
        default = str(Path.home() / f"disk-analyzer.{kind}")
        path, _ = QFileDialog.getSaveFileName(self, title, default, flt)
        if not path:
            return
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            if kind == "csv":
                export_csv(self.root, path)
            else:
                export_json(self.root, self.stats, path)
        except OSError as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, t.t("error_title"), t.t("export_fail", error=str(exc)))
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, t.t("info_title"), t.t("export_ok", path=path))

    def _show_about(self) -> None:
        t = self.tr_
        text = t.t("about_text", version=__version__, author=AUTHOR, note=t.t("readonly_note"), copyright=COPYRIGHT)
        box = QMessageBox(self)
        box.setWindowTitle(t.t("about"))
        box.setText(f"<b>{APP_NAME}</b>")
        box.setInformativeText(text)
        icon = resource_path("assets", "icon.png")
        if icon.is_file():
            box.setIconPixmap(
                QPixmap(str(icon)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        box.exec()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
