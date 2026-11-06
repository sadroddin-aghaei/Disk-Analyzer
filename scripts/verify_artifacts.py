"""Verify build artifacts: real binary architecture, contents, smoke test, checksums.

Sub-commands
  runner    --expect x64|arm64
  windows   --zip FILE --arch x64|arm64
  macos     --dmg FILE --arch x64|arm64 --version X.Y.Z
  checksums --dir DIR --version X.Y.Z      (write SHA256SUMS)
  verify-checksums --dir DIR --version X.Y.Z
  final     --dir DIR --version X.Y.Z      (all four artifacts present)

Exit status is non-zero on any failure; nothing is ever reported as verified unless checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from common import TARGETS, artifact_name, checksums_name, host_arch, normalize_arch

PE_MACHINES = {0x8664: "x64", 0xAA64: "arm64", 0xA641: "arm64ec", 0x14C: "x86"}
MACHO_CPUS = {0x01000007: "x64", 0x0100000C: "arm64", 0x7: "x86"}


class VerificationError(Exception):
    pass


# ----------------------------------------------------------------- binaries
def pe_arch(path: Path) -> str:
    with open(path, "rb") as fh:
        head = fh.read(0x40)
        if len(head) < 0x40 or head[:2] != b"MZ":
            raise VerificationError(f"{path.name}: not a PE file")
        (pe_off,) = struct.unpack("<I", head[0x3C:0x40])
        fh.seek(pe_off)
        sig = fh.read(6)
    if len(sig) < 6 or sig[:4] != b"PE\0\0":
        raise VerificationError(f"{path.name}: invalid PE signature")
    (machine,) = struct.unpack("<H", sig[4:6])
    return PE_MACHINES.get(machine, f"unknown(0x{machine:04x})")


def macho_archs(path: Path) -> set[str]:
    with open(path, "rb") as fh:
        head = fh.read(8)
        if len(head) < 8:
            raise VerificationError(f"{path.name}: too small for Mach-O")
        magic_be = struct.unpack(">I", head[:4])[0]
        if magic_be in (0xCAFEBABE, 0xCAFEBABF):
            count = struct.unpack(">I", head[4:8])[0]
            entry = 20 if magic_be == 0xCAFEBABE else 32
            if not 0 < count < 16:
                raise VerificationError(f"{path.name}: not a Mach-O fat binary")
            archs: set[str] = set()
            for _ in range(count):
                raw = fh.read(entry)
                cpu = struct.unpack(">I", raw[:4])[0]
                archs.add(MACHO_CPUS.get(cpu, f"unknown(0x{cpu:08x})"))
            return archs
        magic_le = struct.unpack("<I", head[:4])[0]
        if magic_le in (0xFEEDFACF, 0xFEEDFACE):
            cpu = struct.unpack("<I", head[4:8])[0]
            return {MACHO_CPUS.get(cpu, f"unknown(0x{cpu:08x})")}
    raise VerificationError(f"{path.name}: not a Mach-O file")


# ------------------------------------------------------------------ helpers
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_smoke(exe: Path, arch: str, version: str | None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "smoke.json"
        env = {"QT_QPA_PLATFORM": "offscreen"}
        import os

        proc = subprocess.run(
            [str(exe), "--smoke-test", "--smoke-test-output", str(out)],
            env={**os.environ, **env},
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0 or not out.is_file():
            raise VerificationError(
                f"smoke test failed (exit {proc.returncode})\nstdout: {proc.stdout[-1500:]}\nstderr: {proc.stderr[-1500:]}"
            )
        data = json.loads(out.read_text(encoding="utf-8"))
    if not data.get("ok"):
        raise VerificationError(f"smoke test reported failure: {data}")
    if not data.get("frozen"):
        raise VerificationError("smoke test did not run from a frozen build")
    if normalize_arch(data["machine"]) != arch:
        raise VerificationError(f"process architecture {data['machine']} != expected {arch}")
    if version and data.get("version") != version:
        raise VerificationError(f"embedded version {data.get('version')} != {version}")
    if not data.get("font_loaded"):
        raise VerificationError("bundled Vazirmatn font failed to load")
    return data


def require_files(root: Path, names: list[str]) -> None:
    missing = [n for n in names if not any(root.rglob(n))]
    if missing:
        raise VerificationError("package is missing required files: " + ", ".join(missing))


# --------------------------------------------------------------- sub-commands
def cmd_runner(expect: str) -> None:
    actual = host_arch()
    print(f"runner architecture: {actual} (expected {expect})")
    if actual != expect:
        raise VerificationError(f"runner is {actual}, expected {expect}: refusing to build a mislabeled artifact")


def cmd_windows(zip_path: Path, arch: str, version: str | None, skip_smoke: bool = False) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as zf:
            bad = zf.testzip()
            if bad:
                raise VerificationError(f"corrupt zip member: {bad}")
            zf.extractall(tmp)
        root = Path(tmp)
        exes = list(root.rglob("DiskAnalyzer.exe"))
        if len(exes) != 1:
            raise VerificationError(f"expected exactly one DiskAnalyzer.exe, found {len(exes)}")
        exe = exes[0]
        got = pe_arch(exe)
        print(f"DiskAnalyzer.exe machine type: {got}")
        if got != arch:
            raise VerificationError(f"DiskAnalyzer.exe is {got}, expected {arch}")

        allowed = {arch} | ({"arm64ec"} if arch == "arm64" else set())
        checked, mismatches = 0, []
        for f in list(root.rglob("*.dll")) + list(root.rglob("*.pyd")):
            try:
                m = pe_arch(f)
            except VerificationError:
                continue
            checked += 1
            if m not in allowed:
                mismatches.append(f"{f.name}={m}")
        print(f"checked {checked} DLL/PYD files")
        if mismatches:
            raise VerificationError("binaries with wrong architecture: " + ", ".join(mismatches[:15]))
        for key in ("Qt6Core.dll", "Qt6Widgets.dll", "Qt6Gui.dll"):
            if not any(root.rglob(key)):
                raise VerificationError(f"missing {key}")

        require_files(
            root, ["LICENSE", "INSTALL.txt", "THIRD-PARTY-NOTICES.txt", "Vazirmatn-Regular.ttf", "icon.png", "qwindows.dll"]
        )
        if not skip_smoke:
            data = run_smoke(exe, arch, version)
            print("smoke test OK:", json.dumps(data))
    print(f"OK  {zip_path.name}")


def cmd_macos(dmg: Path, arch: str, version: str | None, skip_smoke: bool = False) -> None:
    mount = Path(tempfile.mkdtemp(prefix="da-dmg-"))
    subprocess.run(
        ["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly", "-mountpoint", str(mount)], check=True, capture_output=True
    )
    try:
        apps = list(mount.glob("*.app"))
        if len(apps) != 1:
            raise VerificationError(f"expected one .app in the DMG, found {len(apps)}")
        app = apps[0]
        binary = app / "Contents" / "MacOS" / "DiskAnalyzer"
        archs = macho_archs(binary)
        print(f"{binary.name} architectures: {sorted(archs)}")
        if archs != {arch}:
            raise VerificationError(f"main binary is {sorted(archs)}, expected exactly {{{arch}}}")

        checked, mismatches = 0, []
        for f in list(app.rglob("*.so")) + list(app.rglob("*.dylib")) + list(app.glob("Contents/Frameworks/**/Qt*")):
            if not f.is_file() or f.is_symlink():
                continue
            try:
                a = macho_archs(f)
            except (VerificationError, OSError):
                continue
            checked += 1
            if arch not in a:
                mismatches.append(f"{f.name}={sorted(a)}")
        print(f"checked {checked} Mach-O libraries")
        if mismatches:
            raise VerificationError("libraries lacking the target architecture: " + ", ".join(mismatches[:15]))

        plist = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
        if plist.get("CFBundleExecutable") != "DiskAnalyzer":
            raise VerificationError("Info.plist CFBundleExecutable mismatch")
        if version and plist.get("CFBundleShortVersionString") != version.split("-")[0].split("+")[0]:
            raise VerificationError(f"Info.plist version {plist.get('CFBundleShortVersionString')} != {version}")
        require_files(app, ["Vazirmatn-Regular.ttf", "icon.png"])
        for name in ("LICENSE", "INSTALL.txt"):
            if not (mount / name).is_file():
                raise VerificationError(f"DMG is missing {name}")
        if not skip_smoke:
            data = run_smoke(binary, arch, version)
            print("smoke test OK:", json.dumps(data))
    finally:
        subprocess.run(["hdiutil", "detach", str(mount), "-force"], capture_output=True)
        shutil.rmtree(mount, ignore_errors=True)
    print(f"OK  {dmg.name}")


def check_final(directory: Path, version: str) -> list[Path]:
    paths = []
    for target in TARGETS:
        p = directory / artifact_name(version, target)
        if not p.is_file() or p.stat().st_size == 0:
            raise VerificationError(f"required artifact missing or empty: {p.name}")
        paths.append(p)
    return paths


def write_checksums(directory: Path, version: str) -> Path:
    paths = check_final(directory, version)
    out = directory / checksums_name(version)
    out.write_text("".join(f"{sha256_of(p)}  {p.name}\n" for p in paths), encoding="utf-8")
    return out


def verify_checksums(directory: Path, version: str) -> None:
    sums = directory / checksums_name(version)
    if not sums.is_file():
        raise VerificationError(f"{sums.name} not found")
    listed: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        listed[name] = digest
    for p in check_final(directory, version):
        if listed.get(p.name) != sha256_of(p):
            raise VerificationError(f"checksum mismatch for {p.name}")
    print("all SHA256 checksums verified")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("runner")
    r.add_argument("--expect", required=True, choices=["x64", "arm64"])
    w = sub.add_parser("windows")
    w.add_argument("--zip", required=True, type=Path)
    w.add_argument("--arch", required=True, choices=["x64", "arm64"])
    w.add_argument("--version")
    m = sub.add_parser("macos")
    m.add_argument("--dmg", required=True, type=Path)
    m.add_argument("--arch", required=True, choices=["x64", "arm64"])
    m.add_argument("--version")
    for name in ("checksums", "verify-checksums", "final"):
        c = sub.add_parser(name)
        c.add_argument("--dir", required=True, type=Path)
        c.add_argument("--version", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "runner":
            cmd_runner(args.expect)
        elif args.cmd == "windows":
            cmd_windows(args.zip, args.arch, args.version)
        elif args.cmd == "macos":
            cmd_macos(args.dmg, args.arch, args.version)
        elif args.cmd == "checksums":
            print("wrote", write_checksums(args.dir, args.version))
        elif args.cmd == "verify-checksums":
            verify_checksums(args.dir, args.version)
        elif args.cmd == "final":
            for p in check_final(args.dir, args.version):
                print("found", p.name, p.stat().st_size, "bytes")
    except (VerificationError, subprocess.SubprocessError, OSError, ValueError) as exc:
        print(f"VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
