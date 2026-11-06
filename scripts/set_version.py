"""Stamp the application version: python scripts/set_version.py 1.2.3"""

from __future__ import annotations

import sys
from pathlib import Path

from common import normalize_version


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    version = normalize_version(sys.argv[1])
    target = Path(__file__).resolve().parent.parent / "app" / "_version.py"
    target.write_text(
        f'"""Version stamp. Overwritten by scripts/set_version.py during release builds."""\n\n__version__ = "{version}"\n',
        encoding="utf-8",
    )
    print(f"version set to {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
