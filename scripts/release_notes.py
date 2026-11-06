"""Write the hand-written part of the GitHub release notes to stdout.

python scripts/release_notes.py <version> <tag>
"""

from __future__ import annotations

import sys

from common import TARGETS, artifact_name, checksums_name, normalize_version

DESCRIPTIONS = {
    "windows-x64": "Windows 10/11 — Intel/AMD 64-bit (x86_64)",
    "windows-arm64": "Windows 11 — ARM64 (native)",
    "macos-arm64": "macOS — Apple Silicon (M1 and newer, native arm64)",
    "macos-intel": "macOS — Intel (native x86_64)",
}


def main() -> int:
    version = normalize_version(sys.argv[1])
    lines = [
        f"## Disk Analyzer v{version}",
        "",
        "Read-only disk usage analyzer with an interactive treemap — Persian (RTL) and English.",
        "",
        "### Downloads",
        "",
        "| Platform | File |",
        "|---|---|",
    ]
    for key, desc in DESCRIPTIONS.items():
        lines.append(f"| {desc} | `{artifact_name(version, key)}` |")
    lines += [
        "",
        f"Verify downloads with `{checksums_name(version)}` (`shasum -a 256 -c` / `certutil -hashfile <file> SHA256`).",
        "",
        "### Important",
        "",
        "- Every package was built on a native runner of its own architecture; its binaries were inspected and the app was started headless (smoke test) before this release was created.",
        "- **Builds are not code-signed and macOS builds are not notarized.** Windows SmartScreen and macOS Gatekeeper will warn on first launch — see `INSTALL.txt` inside each package.",
        "- Disk Analyzer never modifies files and never sends file names or paths anywhere.",
        "",
        "### Changes",
        "",
    ]
    print("\n".join(lines))
    _ = TARGETS
    return 0


if __name__ == "__main__":
    sys.exit(main())
