# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec shared by all platforms (one-folder build; macOS gets an .app bundle).

Environment variables (all optional):
  DISK_ANALYZER_VERSION       SemVer string embedded in bundle metadata
  DISK_ANALYZER_VERSION_FILE  Windows VSVersionInfo file
  CODESIGN_IDENTITY           macOS signing identity (unsigned/ad-hoc when empty)
"""
import os
import platform
import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 - provided by PyInstaller
VERSION = os.environ.get("DISK_ANALYZER_VERSION", "1.0.0")
CORE_VERSION = re.match(r"\d+\.\d+\.\d+", VERSION).group(0)
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
# Explicit macOS target arch: universal2 Qt wheels get thinned to the native architecture.
MAC_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x86_64"}.get(platform.machine().lower()) if IS_MAC else None

icon = None
if IS_WIN:
    icon = str(ROOT / "assets" / "icon.ico")
elif IS_MAC:
    icon = str(ROOT / "assets" / "icon.icns")

version_file = os.environ.get("DISK_ANALYZER_VERSION_FILE") or None

datas = [
    (str(ROOT / "app" / "resources"), "app/resources"),
    (str(ROOT / "assets" / "icon.png"), "assets"),
]

# Only QtCore/QtGui/QtWidgets are used: keep the bundle lean.
excludes = [
    "tkinter", "unittest", "pytest", "PIL",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.Qt3DCore",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtPositioning", "PySide6.QtRemoteObjects",
]  # fmt: skip

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DiskAnalyzer",
    console=False,
    debug=False,
    strip=False,
    upx=False,
    icon=icon,
    version=version_file,
    target_arch=MAC_ARCH,
    codesign_identity=os.environ.get("CODESIGN_IDENTITY") or None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DiskAnalyzer",
)

if IS_MAC:
    app = BUNDLE(  # noqa: F821
        coll,
        name="Disk Analyzer.app",
        icon=icon,
        bundle_identifier="com.sadroddinaghaei.diskanalyzer",
        info_plist={
            "CFBundleName": "Disk Analyzer",
            "CFBundleDisplayName": "Disk Analyzer",
            "CFBundleExecutable": "DiskAnalyzer",
            "CFBundleShortVersionString": CORE_VERSION,
            "CFBundleVersion": CORE_VERSION,
            "NSHumanReadableCopyright": "© 2026 Sadroddin Aghaei. All rights reserved.",
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSApplicationCategoryType": "public.app-category.utilities",
            "NSDesktopFolderUsageDescription": "Disk Analyzer reads folder sizes to show disk usage. It never modifies files.",
            "NSDocumentsFolderUsageDescription": "Disk Analyzer reads folder sizes to show disk usage. It never modifies files.",
            "NSDownloadsFolderUsageDescription": "Disk Analyzer reads folder sizes to show disk usage. It never modifies files.",
            "NSRemovableVolumesUsageDescription": "Disk Analyzer reads folder sizes to show disk usage. It never modifies files.",
        },
    )
