"""Small reusable widgets: elided label, donut chart, drive card, size-bar delegate."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import BORDER, MUTED


class ElidedLabel(QLabel):
    """Single-line label that elides its middle instead of widening the layout."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(10)

    def setFullText(self, text: str) -> None:  # noqa: N802 - Qt style
        self._full = text
        self.setToolTip(text)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setPen(self.palette().color(self.foregroundRole()))
        text = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, self.width())
        p.drawText(self.rect(), int(self.alignment()) | int(Qt.AlignmentFlag.AlignVCenter), text)


class DonutWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slices: list[tuple[str, float]] = []
        self._center = ""
        self.setMinimumSize(110, 110)

    def set_data(self, slices: list[tuple[str, float]], center_text: str = "") -> None:
        self._slices = [(c, v) for c, v in slices if v > 0]
        self._center = center_text
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 14
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        width = max(10.0, side * 0.16)
        rect.adjust(width / 2, width / 2, -width / 2, -width / 2)
        total = sum(v for _, v in self._slices)
        if total <= 0:
            pen = QPen(QColor(BORDER), width)
            p.setPen(pen)
            p.drawArc(rect, 0, 360 * 16)
        else:
            start = 90 * 16
            for color, value in self._slices:
                span = -int(value / total * 360 * 16)
                p.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                p.drawArc(rect, start, span)
                start += span
        p.setPen(QColor(MUTED))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._center)


class DriveCard(QWidget):
    """Drive name + capacity bar + 'free of total' caption."""

    def __init__(self, title: str, caption: str, percent: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        self.title = QLabel(title)
        self.title.setObjectName("value")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(int(percent))
        self.bar.setTextVisible(False)
        self.caption = QLabel(caption)
        self.caption.setObjectName("muted")
        for w in (self.title, self.bar, self.caption):
            layout.addWidget(w)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


SIZE_FRACTION_ROLE = int(Qt.ItemDataRole.UserRole) + 1
COLOR_ROLE = int(Qt.ItemDataRole.UserRole) + 2


class SizeBarDelegate(QStyledItemDelegate):
    """Paints a proportional coloured bar behind the size text (RTL aware)."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

        frac = float(index.data(SIZE_FRACTION_ROLE) or 0.0)
        color = QColor(index.data(COLOR_ROLE) or MUTED)
        color.setAlpha(80)
        rtl = option.direction == Qt.LayoutDirection.RightToLeft
        r = QRectF(option.rect).adjusted(2, 4, -2, -4)
        w = max(2.0, r.width() * min(1.0, frac)) if frac > 0 else 0.0
        bar = QRectF(r.right() - w if rtl else r.left(), r.top(), w, r.height())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(bar, 4, 4)
        painter.setPen(option.palette.text().color())
        align = Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft)
        painter.drawText(r.adjusted(6, 0, -6, 0), int(align), text)
        painter.restore()
