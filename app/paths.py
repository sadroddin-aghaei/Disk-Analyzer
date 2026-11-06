"""Resource and configuration path helpers (work from source and when frozen)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def base_dir() -> Path:
    """Project root when running from source, PyInstaller bundle dir when frozen."""
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    return base_dir().joinpath(*parts)


def config_dir() -> Path:
    """Per-user configuration directory (created lazily by callers)."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "DiskAnalyzer"
