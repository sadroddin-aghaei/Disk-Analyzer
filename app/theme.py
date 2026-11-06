"""OLED-black dark theme (QSS) and font loading."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.paths import resource_path

BG = "#000000"
PANEL = "#0B1020"
CARD = "#10162A"
CARD_ALT = "#151C33"
BORDER = "#1C2540"
TEXT = "#E8ECF6"
MUTED = "#8A94B0"
ACCENT = "#4C8DFF"
OK = "#3DDC84"
FONT_FAMILY = "Vazirmatn"

STYLESHEET = f"""
* {{ outline: none; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-size: 13px; }}
QFrame#header, QFrame#statusbar {{ background: {PANEL}; border: none; }}
QFrame#sidebar, QFrame#rightpanel {{ background: {PANEL}; border: none; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel {{ background: transparent; }}
QLabel#brand {{ font-size: 17px; font-weight: 700; }}
QLabel#chip {{ background: {CARD_ALT}; border-radius: 10px; padding: 3px 10px; color: {MUTED}; }}
QLabel#section {{ color: {MUTED}; font-weight: 600; }}
QLabel#value {{ font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QPushButton, QToolButton {{ background: {CARD_ALT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 14px; }}
QPushButton:hover, QToolButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #4A5270; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: #04112B; font-weight: 700; }}
QPushButton#primary:disabled {{ background: #1A2A4D; color: #4A5270; border-color: #1A2A4D; }}
QToolButton::menu-indicator {{ image: none; }}
QLineEdit, QComboBox {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 10px; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {BORDER}; selection-background-color: {CARD_ALT}; }}
QListWidget, QTreeWidget {{ background: transparent; border: none; alternate-background-color: transparent; }}
QListWidget::item, QTreeWidget::item {{ padding: 3px 2px; border-radius: 6px; }}
QListWidget::item:selected, QTreeWidget::item:selected {{ background: {CARD_ALT}; }}
QListWidget::item:hover, QTreeWidget::item:hover {{ background: #121A30; }}
QHeaderView {{ background: {PANEL}; border: none; }}
QAbstractScrollArea::corner {{ background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QHeaderView::section {{ background: transparent; color: {MUTED}; border: none; padding: 4px 6px; }}
QProgressBar {{ background: {CARD_ALT}; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; }}
QProgressBar::chunk {{ background: {OK}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 24px; }}
QScrollArea {{ background: transparent; border: none; }}
QMenu {{ background: {CARD}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {CARD_ALT}; }}
QToolTip {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; }}
QMessageBox, QDialog {{ background: {PANEL}; }}
"""


def load_fonts(app: QApplication) -> bool:
    """Register bundled Vazirmatn and make it the application font. Returns True if loaded."""
    loaded = False
    font_dir = resource_path("app", "resources", "fonts")
    for name in ("Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf"):
        path = font_dir / name
        if path.is_file() and QFontDatabase.addApplicationFont(str(path)) >= 0:
            loaded = True
    font = QFont(FONT_FAMILY if loaded else app.font().family())
    font.setPointSize(10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    return loaded
