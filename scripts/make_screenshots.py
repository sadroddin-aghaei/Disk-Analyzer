"""Render real screenshots of the app (offscreen) for the README.

Usage: python scripts/make_screenshots.py [folder-to-scan]

Without an argument a synthetic demo tree (sparse files, no real disk usage) is scanned.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.scanner import Scanner
from app.settings import Settings
from app.theme import STYLESHEET, load_fonts

DEMO = {
    "Movies": [("holiday-2025.mp4", 9.2), ("wedding.mkv", 6.1), ("trailer.mov", 1.4), ("clips.avi", 2.2)],
    "Photos/2024": [(f"IMG_{i:04d}.jpg", 0.012 * (1 + i % 5)) for i in range(180)],
    "Photos/RAW": [(f"DSC_{i:04d}.nef", 0.05) for i in range(120)],
    "Music": [(f"track{i:02d}.flac", 0.03) for i in range(120)],
    "Documents": [("thesis.pdf", 0.08), ("budget.xlsx", 0.01), ("slides.pptx", 0.2), ("notes.txt", 0.001)] * 8,
    "Backups": [("laptop.zip", 5.4), ("disk.iso", 4.7), ("site.tar.gz", 1.2)],
    "Projects/web": [(f"module{i}.js", 0.002) for i in range(300)] + [("data.json", 0.4)],
    "Applications": [("Editor.app", 3.1), ("Setup.exe", 0.9), ("tool.dmg", 1.8)],
    "Library/Caches": [(f"cache{i}.db", 0.04) for i in range(150)],
}


def make_demo(base: Path) -> None:
    for folder, files in DEMO.items():
        d = base / folder
        d.mkdir(parents=True, exist_ok=True)
        for name, gb in files:
            with open(d / name, "ab") as fh:
                fh.truncate(int(gb * 1024**3))


def main() -> None:
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = str(Path(tempfile.mkdtemp(prefix="DiskAnalyzerDemo-")) / "Demo")
        Path(target).mkdir()
        make_demo(Path(target))
    out = Path(__file__).resolve().parent.parent / "docs"
    out.mkdir(exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    load_fonts(app)
    app.setStyleSheet(STYLESHEET)
    scanner = Scanner()
    root = scanner.scan(target)
    win = MainWindow(Settings(), persist_settings=False)
    win.resize(1440, 860)
    win.selected_path = target
    for lang in ("fa", "en"):
        win.set_language(lang)
        win.show_result(root, scanner.stats)
        win.show()
        app.processEvents()
        win.treemap._relayout()
        win.treemap._opacity = 1.0
        app.processEvents()
        win.grab().save(str(out / f"screenshot-{lang}.png"))
        print("saved", out / f"screenshot-{lang}.png")


if __name__ == "__main__":
    main()
