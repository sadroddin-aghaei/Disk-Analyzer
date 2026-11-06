"""Headless smoke test used by CI to prove a (frozen) build actually starts."""

from __future__ import annotations

import json
import platform
import struct
import sys
import tempfile
from pathlib import Path


def run_smoke_test(output: str | None) -> int:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import __version__ as pyside_version
    from PySide6.QtWidgets import QApplication

    from app import __version__
    from app.main_window import MainWindow
    from app.scanner import Scanner
    from app.settings import Settings
    from app.theme import STYLESHEET, load_fonts

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    font_ok = load_fonts(app)
    app.setStyleSheet(STYLESHEET)

    with tempfile.TemporaryDirectory(prefix="disk-analyzer-smoke-") as tmp:
        base = Path(tmp)
        (base / "a" / "b").mkdir(parents=True)
        (base / "movie.mp4").write_bytes(b"x" * 4096)
        (base / "a" / "doc.pdf").write_bytes(b"x" * 2048)
        (base / "a" / "b" / "code.py").write_bytes(b"x" * 512)
        scanner = Scanner()
        root = scanner.scan(base)

        win = MainWindow(Settings(), persist_settings=False)
        win.show_result(root, scanner.stats)
        win.resize(1200, 760)
        app.processEvents()
        win.treemap._relayout()  # force a synchronous layout
        pixmap = win.grab()
        result = {
            "ok": root.files == 3 and root.size == 6656 and not pixmap.isNull(),
            "version": __version__,
            "machine": platform.machine(),
            "system": platform.system(),
            "pointer_bits": struct.calcsize("P") * 8,
            "python": platform.python_version(),
            "pyside6": pyside_version,
            "frozen": bool(getattr(sys, "frozen", False)),
            "font_loaded": font_ok,
            "files": root.files,
            "tiles": win.treemap.tile_count,
        }
        win.close()

    text = json.dumps(result, indent=2)
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if result["ok"] else 1
