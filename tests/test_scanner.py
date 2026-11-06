import os
import sys

import pytest

from app.file_categories import category_of, extension_of
from app.scanner import ScanCancelledError, Scanner, largest_files, largest_folders, search, walk


def test_sizes_and_counts(sample_tree):
    sc = Scanner()
    root = sc.scan(sample_tree)
    assert root.size == 7110
    assert root.files == 4
    assert root.dirs == 3  # a, a/b, empty
    assert sc.stats.files == 4 and sc.stats.dirs == 3 and sc.stats.bytes == 7110
    a = next(c for c in root.children if c.name == "a")
    assert a.size == 2100 and a.files == 2


def test_children_sorted_by_size(sample_tree):
    root = Scanner().scan(sample_tree)
    sizes = [c.size for c in root.children]
    assert sizes == sorted(sizes, reverse=True)


def test_paths(sample_tree):
    root = Scanner().scan(sample_tree)
    leaf = next(n for n in walk(root) if n.name == "c.py")
    assert leaf.path == str(sample_tree / "a" / "b" / "c.py")


def test_categories(sample_tree):
    sc = Scanner()
    root = sc.scan(sample_tree)
    assert sc.stats.cat_sizes["video"] == 5000
    assert sc.stats.cat_sizes["documents"] == 2010
    assert sc.stats.cat_sizes["code"] == 100
    assert root.category == "video"


def test_category_helpers():
    assert extension_of("Archive.TAR.GZ") == "gz"
    assert extension_of(".bashrc") == ""
    assert extension_of("noext") == ""
    assert category_of("Movie.MKV") == "video"
    assert category_of("weird.zzz") == "other"


def test_aggregate_keeps_totals(tmp_path):
    for i in range(10):
        (tmp_path / f"f{i}.bin").write_bytes(b"x" * (i + 1))
    root = Scanner(max_files_per_dir=3).scan(tmp_path)
    assert root.size == 55 and root.files == 10
    assert len(root.children) == 4
    agg = [c for c in root.children if c.is_aggregate]
    assert len(agg) == 1 and agg[0].files == 7 and agg[0].size == 1 + 2 + 3 + 4 + 5 + 6 + 7


def test_largest_and_search(sample_tree):
    root = Scanner().scan(sample_tree)
    assert [n.name for n in largest_files(root, 2)] == ["movie.mp4", "doc.pdf"]
    assert largest_folders(root, 1)[0].name == "a"  # own size 2000 > b's 100
    assert [n.name for n in search(root, "DOC")] == ["doc.pdf"]
    assert {n.name for n in search(root, "", category="code")} == {"b", "c.py"}  # folder b is code-dominant


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges on Windows")
def test_symlink_loop_is_not_followed(tmp_path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "f.txt").write_bytes(b"x" * 10)
    os.symlink(tmp_path, tmp_path / "d" / "loop")  # d/loop -> root (cycle)
    os.symlink(tmp_path / "d" / "f.txt", tmp_path / "link.txt")
    sc = Scanner()
    root = sc.scan(tmp_path)
    assert root.size == 10 and root.files == 1
    assert sc.stats.skipped_links == 2


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions, non-root")
def test_permission_error_is_recorded_not_raised(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "secret.txt").write_bytes(b"x" * 50)
    (tmp_path / "ok.txt").write_bytes(b"x" * 5)
    locked.chmod(0o000)
    try:
        sc = Scanner()
        root = sc.scan(tmp_path)
    finally:
        locked.chmod(0o700)
    assert root.size == 5
    assert sc.stats.error_count == 1
    assert next(c for c in root.children if c.name == "locked").error


def test_permission_error_simulated(monkeypatch, sample_tree):
    """Platform independent: make scandir fail for one directory."""
    real = os.scandir
    target = str(sample_tree / "a")

    def fake(path):
        if str(path) == target:
            raise PermissionError(13, "Permission denied", str(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", fake)
    sc = Scanner()
    root = sc.scan(sample_tree)
    assert root.size == 5010
    assert sc.stats.error_count == 1
    assert sc.stats.errors[0].message.startswith("PermissionError")


def test_cancel(sample_tree):
    sc = Scanner()
    sc.cancel()  # cancel() before scan() is cleared by scan(); cancel from callback instead
    calls = []

    def cb(stats, path):
        calls.append(path)
        sc.cancel()

    sc = Scanner(cb, progress_interval=0.0)
    with pytest.raises(ScanCancelledError):
        sc.scan(sample_tree)
    assert calls


def test_invalid_roots(tmp_path):
    with pytest.raises(FileNotFoundError):
        Scanner().scan(tmp_path / "missing")
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        Scanner().scan(f)


def test_scan_never_modifies_tree(sample_tree):
    def snapshot():
        return sorted((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in sample_tree.rglob("*"))

    before = snapshot()
    Scanner().scan(sample_tree)
    assert snapshot() == before
