"""Build the Windows ZIP package with PyInstaller.

    python scripts/build_windows.py --version 1.0.0 --arch x64|arm64

The script refuses to run if the host architecture differs from --arch, so an
x64 executable can never be labelled ARM64 (or vice-versa).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from common import TARGETS, artifact_name, core_version, host_arch, normalize_version
from verify_artifacts import VerificationError, pe_arch

ROOT = Path(__file__).resolve().parent.parent

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({maj}, {min}, {pat}, 0), prodvers=({maj}, {min}, {pat}, 0),
                    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Sadroddin Aghaei'),
      StringStruct('FileDescription', 'Disk Analyzer'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', 'DiskAnalyzer'),
      StringStruct('LegalCopyright', '\\xa9 2026 Sadroddin Aghaei. All rights reserved.'),
      StringStruct('OriginalFilename', 'DiskAnalyzer.exe'),
      StringStruct('ProductName', 'Disk Analyzer'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--arch", required=True, choices=["x64", "arm64"])
    ap.add_argument("--out", type=Path, default=ROOT / "release")
    args = ap.parse_args()

    version = normalize_version(args.version)
    if sys.platform != "win32":
        print("error: this script builds Windows packages and must run on Windows", file=sys.stderr)
        return 2
    if host_arch() != args.arch:
        print(f"error: host is {host_arch()} but --arch {args.arch} was requested", file=sys.stderr)
        return 2

    target = f"windows-{args.arch}"
    work = ROOT / "build"
    dist = ROOT / "dist"
    for d in (work, dist):
        shutil.rmtree(d, ignore_errors=True)
    args.out.mkdir(parents=True, exist_ok=True)

    maj, minor, pat = (int(x) for x in core_version(version).split("."))
    vfile = work / "version_info.txt"
    work.mkdir(parents=True, exist_ok=True)
    vfile.write_text(VERSION_INFO.format(maj=maj, min=minor, pat=pat, ver=f"{maj}.{minor}.{pat}.0"), encoding="utf-8")
    env = {**os.environ, "DISK_ANALYZER_VERSION": version, "DISK_ANALYZER_VERSION_FILE": str(vfile)}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            str(work / "pyi"),
            "--distpath",
            str(dist),
            str(ROOT / "DiskAnalyzer.spec"),
        ],
        check=True,
        cwd=ROOT,
        env=env,
    )

    app_dir = dist / "DiskAnalyzer"
    exe = app_dir / "DiskAnalyzer.exe"
    if not exe.is_file():
        print("error: PyInstaller did not produce DiskAnalyzer.exe", file=sys.stderr)
        return 1
    try:
        actual = pe_arch(exe)
    except VerificationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if actual != args.arch:
        print(f"error: built executable is {actual}, expected {args.arch}", file=sys.stderr)
        return 1

    pkg_name = artifact_name(version, target).removesuffix(".zip")
    stage = work / "package" / pkg_name
    shutil.copytree(app_dir, stage)
    for src, dst in (
        (ROOT / "LICENSE", "LICENSE"),
        (ROOT / "THIRD-PARTY-NOTICES.txt", "THIRD-PARTY-NOTICES.txt"),
        (ROOT / "packaging" / "INSTALL-windows.txt", "INSTALL.txt"),
    ):
        shutil.copy2(src, stage / dst)

    zip_path = args.out / artifact_name(version, target)
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, Path(pkg_name) / path.relative_to(stage))
    print(f"built {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB), exe machine type: {actual}")
    _ = TARGETS  # keep import for documentation of valid targets
    return 0


if __name__ == "__main__":
    sys.exit(main())
