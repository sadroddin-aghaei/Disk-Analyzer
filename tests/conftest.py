import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """root/ a/(b/(c.py 100) doc.pdf 2000) movie.mp4 5000 notes.txt 10 empty/"""
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "empty").mkdir()
    (tmp_path / "a" / "b" / "c.py").write_bytes(b"x" * 100)
    (tmp_path / "a" / "doc.pdf").write_bytes(b"x" * 2000)
    (tmp_path / "movie.mp4").write_bytes(b"x" * 5000)
    (tmp_path / "notes.txt").write_bytes(b"x" * 10)
    return tmp_path
