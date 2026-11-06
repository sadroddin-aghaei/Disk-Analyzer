"""Print the artifact file name: python scripts/artifact_name.py <version> <target>"""

from __future__ import annotations

import sys

from common import TARGETS, artifact_name, checksums_name, normalize_version


def main() -> int:
    if len(sys.argv) != 3 or (sys.argv[2] not in TARGETS and sys.argv[2] != "checksums"):
        print(f"usage: artifact_name.py <version> <{'|'.join([*TARGETS, 'checksums'])}>", file=sys.stderr)
        return 2
    version = normalize_version(sys.argv[1])
    print(checksums_name(version) if sys.argv[2] == "checksums" else artifact_name(version, sys.argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
