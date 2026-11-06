"""Shared constants/helpers for the build and verification scripts."""

from __future__ import annotations

import platform
import re
from dataclasses import dataclass

SEMVER_RE = re.compile(
    r"^v?(?P<core>(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))"
    r"(?P<pre>-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(?P<build>\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)


@dataclass(frozen=True)
class Target:
    label: str  # used in the file name
    ext: str
    arch: str  # normalised: x64 | arm64
    system: str  # windows | macos
    runner: str


TARGETS: dict[str, Target] = {
    "windows-x64": Target("Windows-x64", "zip", "x64", "windows", "windows-latest"),
    "windows-arm64": Target("Windows-ARM64", "zip", "arm64", "windows", "windows-11-arm"),
    "macos-arm64": Target("macOS-Apple-Silicon-arm64", "dmg", "arm64", "macos", "macos-latest"),
    "macos-intel": Target("macOS-Intel-x86_64", "dmg", "x64", "macos", "macos-15-intel"),
}


def normalize_version(raw: str) -> str:
    """Return the SemVer string without a leading 'v'; raise ValueError if invalid."""
    raw = raw.strip()
    m = SEMVER_RE.match(raw)
    if not m:
        raise ValueError(f"'{raw}' is not a valid Semantic Version (expected e.g. v1.2.3 or 1.2.3-rc.1)")
    return raw[1:] if raw.startswith("v") else raw


def core_version(version: str) -> str:
    m = SEMVER_RE.match(version)
    if not m:
        raise ValueError(version)
    return m.group("core")


def artifact_name(version: str, target: str) -> str:
    t = TARGETS[target]
    return f"Disk-Analyzer-v{version}-{t.label}.{t.ext}"


def checksums_name(version: str) -> str:
    return f"Disk-Analyzer-v{version}-SHA256SUMS.txt"


def normalize_arch(machine: str) -> str:
    m = machine.lower()
    if m in {"amd64", "x86_64", "x64"}:
        return "x64"
    if m in {"arm64", "aarch64"}:
        return "arm64"
    raise ValueError(f"unsupported architecture: {machine}")


def host_arch() -> str:
    return normalize_arch(platform.machine())
