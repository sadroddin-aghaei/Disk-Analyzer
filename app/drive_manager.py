"""Drive / volume discovery (read-only, via psutil)."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

_SKIP_FSTYPES = {
    "squashfs", "tmpfs", "devtmpfs", "overlay", "proc", "sysfs", "cgroup", "cgroup2",
    "autofs", "devfs", "fusectl", "debugfs", "tracefs", "securityfs", "pstore", "mqueue",
}  # fmt: skip


@dataclass(frozen=True, slots=True)
class Drive:
    name: str
    path: str
    fstype: str
    total: int
    used: int
    free: int
    is_home: bool = False

    @property
    def percent(self) -> float:
        return (self.used / self.total * 100.0) if self.total else 0.0


def usage_for(path: str | Path) -> tuple[int, int, int]:
    """(total, used, free) of the filesystem containing ``path``; zeros on error."""
    try:
        u = shutil.disk_usage(path)
        return u.total, u.used, u.free
    except OSError:
        return 0, 0, 0


def _display_name(mount: str) -> str:
    if sys.platform == "win32":
        return mount.rstrip("\\") or mount
    if mount == "/":
        return "/"
    return Path(mount).name or mount


def _should_skip(mount: str, fstype: str, opts: str) -> bool:
    if fstype.lower() in _SKIP_FSTYPES:
        return True
    if "cdrom" in opts and sys.platform == "win32":
        return True
    if sys.platform == "darwin":
        if mount.startswith(("/System/Volumes/", "/private/var/vm", "/Library/Developer")) and mount != "/System/Volumes/Data":
            return True
    elif sys.platform.startswith("linux"):
        if mount.startswith(("/snap/", "/boot/efi", "/sys", "/proc", "/dev", "/run")):
            return True
    return False


def list_drives(include_home: bool = True) -> list[Drive]:
    drives: list[Drive] = []
    seen: set[str] = set()
    try:
        parts = psutil.disk_partitions(all=False)
    except Exception:  # pragma: no cover - psutil platform quirks
        parts = []
    for p in parts:
        if p.mountpoint in seen or _should_skip(p.mountpoint, p.fstype or "", p.opts or ""):
            continue
        total, used, free = usage_for(p.mountpoint)
        if total <= 0:
            continue
        seen.add(p.mountpoint)
        drives.append(Drive(_display_name(p.mountpoint), p.mountpoint, p.fstype or "", total, used, free))
    if include_home:
        home = str(Path.home())
        total, used, free = usage_for(home)
        drives.insert(0, Drive("Home", home, "", total, used, free, is_home=True))
    return drives
