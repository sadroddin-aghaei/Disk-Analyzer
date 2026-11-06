"""Build the macOS .app and DMG with PyInstaller + hdiutil.

    python scripts/build_macos.py --version 1.0.0 --arch arm64|x64

Builds are *unsigned* (ad-hoc signed) unless CODESIGN_IDENTITY is set. They are
NOT notarized; see README for the Gatekeeper steps users must take.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import artifact_name, host_arch, normalize_version
from verify_artifacts import VerificationError, macho_archs

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "Disk Analyzer.app"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--arch", required=True, choices=["x64", "arm64"])
    ap.add_argument("--out", type=Path, default=ROOT / "release")
    args = ap.parse_args()

    version = normalize_version(args.version)
    if sys.platform != "darwin":
        print("error: this script builds macOS packages and must run on macOS", file=sys.stderr)
        return 2
    if host_arch() != args.arch:
        print(f"error: host is {host_arch()} but --arch {args.arch} was requested", file=sys.stderr)
        return 2

    target = "macos-arm64" if args.arch == "arm64" else "macos-intel"
    work, dist = ROOT / "build", ROOT / "dist"
    for d in (work, dist):
        shutil.rmtree(d, ignore_errors=True)
    args.out.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "DISK_ANALYZER_VERSION": version}
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

    app = dist / APP_NAME
    binary = app / "Contents" / "MacOS" / "DiskAnalyzer"
    if not binary.is_file():
        print("error: PyInstaller did not produce the .app bundle", file=sys.stderr)
        return 1
    try:
        archs = macho_archs(binary)
    except VerificationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if archs != {args.arch}:
        print(f"error: built binary is {sorted(archs)}, expected only {args.arch}", file=sys.stderr)
        return 1

    identity = os.environ.get("CODESIGN_IDENTITY", "").strip()
    sign_id = identity or "-"  # "-" = ad-hoc signature (required to run on Apple Silicon)
    subprocess.run(["codesign", "--force", "--deep", "--sign", sign_id, str(app)], check=True)
    print("signed with:", "Developer ID (not notarized)" if identity else "ad-hoc signature (unsigned, not notarized)")

    staging = work / "dmg-root"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    subprocess.run(["ditto", str(app), str(staging / APP_NAME)], check=True)
    (staging / "Applications").symlink_to("/Applications")
    shutil.copy2(ROOT / "LICENSE", staging / "LICENSE")
    shutil.copy2(ROOT / "THIRD-PARTY-NOTICES.txt", staging / "THIRD-PARTY-NOTICES.txt")
    shutil.copy2(ROOT / "packaging" / "INSTALL-macos.txt", staging / "INSTALL.txt")

    dmg = args.out / artifact_name(version, target)
    dmg.unlink(missing_ok=True)
    subprocess.run(
        ["hdiutil", "create", "-volname", "Disk Analyzer", "-srcfolder", str(staging), "-ov", "-format", "UDZO", str(dmg)],
        check=True,
    )
    print(f"built {dmg} ({dmg.stat().st_size / 1e6:.1f} MB), binary architecture: {sorted(archs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
