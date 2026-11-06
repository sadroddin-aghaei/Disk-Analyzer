"""Interactive treemap canvas."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent
from PySide6.QtWidgets import QWidget

from app.file_categories import color_of
from app.scanner import Node
from app.theme import MUTED
from app.treemap import Tile, build_tiles, tile_at


class TreemapWidget(QWidget):
    navigate_requested = Signal(object)  # Node (folder)
    hovered = Signal(object, object)  # Node | None, QPoint(global)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self._root: Node | None = None
        self._tiles: list[Tile] = []
        self._hover: Tile | None = None
        self._placeholder = ""
        self._format_size: Callable[[int], str] = lambda n: str(n)
        self._opacity = 1.0

        self._relayout_timer = QTimer(self)
        self._relayout_timer.setSingleShot(True)
        self._relayout_timer.setInterval(60)
        self._relayout_timer.timeout.connect(self._relayout)

        self._anim = QPropertyAnimation(self, b"revealOpacity", self)
        self._anim.setDuration(380)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- animated property
    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    revealOpacity = Property(float, _get_opacity, _set_opacity)  # noqa: N815

    # ---- public API
    def set_formatter(self, fn: Callable[[int], str]) -> None:
        self._format_size = fn
        self.update()

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        self.update()

    def set_root(self, node: Node | None, animate: bool = False) -> None:
        self._root = node
        self._hover = None
        self._relayout()
        if animate and node is not None:
            self._anim.stop()
            self._anim.start()

    @property
    def tile_count(self) -> int:
        return len(self._tiles)

    # ---- layout
    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_timer.start()

    def _relayout(self) -> None:
        if self._root is None or self.width() < 4 or self.height() < 4:
            self._tiles = []
        else:
            self._tiles = build_tiles(self._root, self.width(), self.height())
        self._hover = None
        self.update()

    # ---- painting
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#000000"))
        if not self._tiles:
            p.setPen(QColor(MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._placeholder)
            return

        p.setOpacity(self._opacity)
        small = QFont(self.font())
        small.setPointSizeF(max(7.0, self.font().pointSizeF() - 1.5))
        bold = QFont(self.font())
        bold.setBold(True)
        fm_small = p.fontMetrics()

        for tile in self._tiles:
            r = tile.rect
            rect = QRectF(r.x + 0.75, r.y + 0.75, max(0.5, r.w - 1.5), max(0.5, r.h - 1.5))
            base = QColor(color_of(tile.node.category))
            if tile.node.is_aggregate:
                base = QColor("#3A4358")
            if tile.depth > 0:
                base = base.darker(100 + 18 * tile.depth)
            if tile.container:
                fill = base.darker(240)
            elif rect.width() * rect.height() > 600:
                grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
                grad.setColorAt(0.0, base.lighter(118))
                grad.setColorAt(1.0, base.darker(125))
                p.setBrush(grad)
                fill = None
            else:
                fill = base
            p.setPen(Qt.PenStyle.NoPen)
            if fill is not None:
                p.setBrush(fill)
            radius = 4.0 if rect.width() > 24 and rect.height() > 24 else 1.0
            p.drawRoundedRect(rect, radius, radius)

            # labels
            if tile.container and tile.header > 0:
                p.setFont(small)
                p.setPen(QColor("#F4F6FB"))
                text = fm_small.elidedText(tile.node.name, Qt.TextElideMode.ElideRight, int(rect.width() - 10))
                p.drawText(rect.adjusted(5, 1, -5, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text)
            elif not tile.container and rect.width() > 70 and rect.height() > 34:
                p.setFont(bold if tile.depth == 0 else small)
                p.setPen(QColor("#FFFFFF"))
                fm = p.fontMetrics()
                name = fm.elidedText(tile.node.name, Qt.TextElideMode.ElideRight, int(rect.width() - 14))
                p.drawText(rect.adjusted(7, 5, -7, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, name)
                if rect.height() > 52:
                    p.setFont(small)
                    p.setPen(QColor(255, 255, 255, 200))
                    p.drawText(
                        rect.adjusted(7, 7 + fm.height(), -7, 0),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        self._format_size(tile.node.size),
                    )

        if self._hover is not None:
            r = self._hover.rect
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#FFFFFF"), 2))
            p.drawRoundedRect(QRectF(r.x + 1, r.y + 1, r.w - 2, r.h - 2), 4, 4)

    # ---- interaction
    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos: QPointF = event.position()
        tile = tile_at(self._tiles, pos.x(), pos.y())
        if tile is not self._hover:
            self._hover = tile
            self.update()
        self.hovered.emit(tile.node if tile else None, event.globalPosition().toPoint())
        self.setCursor(Qt.CursorShape.PointingHandCursor if tile and tile.top.is_dir else Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = None
        self.update()
        self.hovered.emit(None, None)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        tile = tile_at(self._tiles, pos.x(), pos.y())
        if tile is None:
            return
        target = tile.node if tile.node.is_dir else tile.node.parent
        # Click on a nested item navigates to the top-level folder it lives in.
        if tile.top.is_dir:
            target = tile.top
        if target is not None and target.is_dir:
            self.navigate_requested.emit(target)
