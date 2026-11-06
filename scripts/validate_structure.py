"""Fail if required project files are missing (used by CI)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".github/workflows/tests.yml",
    "app/__init__.py",
    "app/_version.py",
    "app/main_window.py",
    "app/scanner.py",
    "app/treemap.py",
    "app/drive_manager.py",
    "app/file_categories.py",
    "app/localization.py",
    "app/settings.py",
    "app/export_manager.py",
    "app/workers.py",
    "app/widgets/treemap_widget.py",
    "app/resources/fonts/Vazirmatn-Regular.ttf",
    "app/resources/fonts/OFL.txt",
    "tests/test_scanner.py",
    "tests/test_treemap.py",
    "tests/test_export.py",
    "tests/test_localization.py",
    "scripts/build_windows.py",
    "scripts/build_macos.py",
    "scripts/verify_artifacts.py",
    "assets/icon.png",
    "assets/icon.ico",
    "assets/icon.icns",
    "main.py",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "README.md",
    "LICENSE",
    ".gitignore",
    "DiskAnalyzer.spec",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    for p in missing:
        print(f"::error::missing required file: {p}")
    if missing:
        return 1
    print(f"project structure OK ({len(REQUIRED)} required paths present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
