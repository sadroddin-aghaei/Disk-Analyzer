"""Disk Analyzer entry point."""

from __future__ import annotations

import argparse
import sys

from app import APP_NAME, __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="DiskAnalyzer", description=f"{APP_NAME} {__version__}")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--smoke-test", action="store_true", help="start headless, scan a temp tree, exit")
    parser.add_argument("--smoke-test-output", metavar="FILE", help="write smoke-test JSON to FILE")
    args, qt_args = parser.parse_known_args(argv)

    if args.smoke_test:
        from app.smoke import run_smoke_test

        return run_smoke_test(args.smoke_test_output)

    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow
    from app.settings import Settings
    from app.theme import STYLESHEET, load_fonts

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Sadroddin Aghaei")
    app.setStyle("Fusion")
    load_fonts(app)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow(Settings.load())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
