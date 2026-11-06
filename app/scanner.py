"""Read-only recursive directory scanner.

Design notes
------------
* Never modifies the filesystem: only ``os.scandir`` / ``stat`` are used.
* Symbolic links and Windows junctions are *not followed* (recursion protection).
* By default the scan stays on the root's filesystem (skips /proc, other mounts).
* Memory is bounded: each directory keeps at most ``max_files_per_dir`` of its
  largest files; the remainder is folded into one aggregate node whose size is
  still counted, so totals remain exact.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from app.file_categories import category_of, extension_of

MAX_DEPTH = 200
MAX_RECORDED_ERRORS = 500

ProgressCallback = Callable[["ScanStats", str], None]


class ScanCancelledError(Exception):
    """Raised when the scan was cancelled by the user."""


@dataclass(eq=False, slots=True)
class Node:
    name: str
    is_dir: bool
    size: int = 0
    files: int = 0  # number of files in this subtree (1 for a file)
    dirs: int = 0  # number of directories in this subtree (excluding itself)
    category: str = "other"
    children: list[Node] = field(default_factory=list)
    parent: Node | None = None
    error: str | None = None
    is_aggregate: bool = False

    @property
    def path(self) -> str:
        parts: list[str] = []
        node: Node | None = self
        while node is not None:
            parts.append(node.name)
            node = node.parent
        parts.reverse()
        if not parts:
            return ""
        return str(Path(parts[0]).joinpath(*parts[1:])) if len(parts) > 1 else parts[0]

    @property
    def own_size(self) -> int:
        """Bytes in files placed directly inside this folder."""
        return self.size - sum(c.size for c in self.children if c.is_dir)

    def ancestors(self) -> list[Node]:
        out: list[Node] = []
        node: Node | None = self
        while node is not None:
            out.append(node)
            node = node.parent
        out.reverse()
        return out


@dataclass(slots=True)
class ScanError:
    path: str
    message: str


@dataclass(slots=True)
class ScanStats:
    files: int = 0
    dirs: int = 0
    bytes: int = 0
    skipped_links: int = 0
    skipped_mounts: int = 0
    error_count: int = 0
    errors: list[ScanError] = field(default_factory=list)
    ext_sizes: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    ext_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cat_sizes: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cat_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    elapsed: float = 0.0


def _is_junction(entry: os.DirEntry[str]) -> bool:
    fn = getattr(entry, "is_junction", None)
    try:
        return bool(fn()) if fn else False
    except OSError:
        return False


class Scanner:
    def __init__(
        self,
        progress: ProgressCallback | None = None,
        *,
        max_files_per_dir: int = 1000,
        progress_interval: float = 0.1,
        one_file_system: bool = True,
    ) -> None:
        self._progress = progress
        self._max_files = max(1, max_files_per_dir)
        self._interval = progress_interval
        self._one_fs = one_file_system
        self._cancel = threading.Event()
        self._last_emit = 0.0
        self._root_dev: int | None = None
        self._seen: set[tuple[int, int]] = set()
        self.stats = ScanStats()

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    # ------------------------------------------------------------------ API
    def scan(self, root: str | os.PathLike[str]) -> Node:
        root_path = Path(root)
        if not root_path.exists():
            raise FileNotFoundError(str(root_path))
        if not root_path.is_dir():
            raise NotADirectoryError(str(root_path))

        self.stats = ScanStats()
        self._cancel.clear()
        self._seen.clear()
        started = time.monotonic()
        try:
            self._root_dev = os.stat(root_path).st_dev if os.name == "posix" else None
        except OSError:
            self._root_dev = None

        node = Node(name=str(root_path), is_dir=True)
        self._scan_dir(node, str(root_path), 0)
        self.stats.elapsed = time.monotonic() - started
        self._emit(str(root_path), force=True)
        return node

    # ------------------------------------------------------------- internals
    def _record_error(self, path: str, exc: BaseException) -> None:
        self.stats.error_count += 1
        if len(self.stats.errors) < MAX_RECORDED_ERRORS:
            self.stats.errors.append(ScanError(path, exc.__class__.__name__ + ": " + str(exc)))

    def _emit(self, path: str, force: bool = False) -> None:
        if self._progress is None:
            return
        now = time.monotonic()
        if force or now - self._last_emit >= self._interval:
            self._last_emit = now
            self._progress(self.stats, path)

    def _scan_dir(self, node: Node, path: str, depth: int) -> dict[str, int]:
        cat_sizes: dict[str, int] = defaultdict(int)
        if depth > MAX_DEPTH:
            node.error = "maximum depth exceeded"
            return cat_sizes

        subdirs: list[tuple[str, str]] = []
        files: list[tuple[str, int]] = []
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if self._cancel.is_set():
                        raise ScanCancelledError
                    try:
                        if entry.is_symlink() or _is_junction(entry):
                            self.stats.skipped_links += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if os.name == "posix":
                                st = entry.stat(follow_symlinks=False)
                                if self._one_fs and self._root_dev is not None and st.st_dev != self._root_dev:
                                    self.stats.skipped_mounts += 1
                                    continue
                                key = (st.st_dev, st.st_ino)
                                if key in self._seen:
                                    self.stats.skipped_links += 1
                                    continue
                                self._seen.add(key)
                            subdirs.append((entry.name, entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            files.append((entry.name, entry.stat(follow_symlinks=False).st_size))
                    except OSError as exc:
                        self._record_error(entry.path, exc)
        except ScanCancelledError:
            raise
        except OSError as exc:
            node.error = f"{exc.__class__.__name__}: {exc}"
            self._record_error(path, exc)
            return cat_sizes

        # ---- files
        files.sort(key=lambda f: f[1], reverse=True)
        kept = files[: self._max_files]
        rest = files[self._max_files :]
        stats = self.stats
        for name, size in files:
            cat = category_of(name)
            ext = extension_of(name)
            cat_sizes[cat] += size
            stats.ext_sizes[ext] += size
            stats.ext_counts[ext] += 1
            stats.cat_sizes[cat] += size
            stats.cat_counts[cat] += 1
        stats.files += len(files)
        stats.bytes += sum(s for _, s in files)

        for name, size in kept:
            node.children.append(Node(name=name, is_dir=False, size=size, files=1, category=category_of(name), parent=node))
        if rest:
            node.children.append(
                Node(
                    name="…",
                    is_dir=False,
                    size=sum(s for _, s in rest),
                    files=len(rest),
                    category="other",
                    parent=node,
                    is_aggregate=True,
                )
            )
        node.size = sum(s for _, s in files)
        node.files = len(files)
        self._emit(path)

        # ---- sub-directories (after the handle is closed)
        for name, full in subdirs:
            if self._cancel.is_set():
                raise ScanCancelledError
            child = Node(name=name, is_dir=True, parent=node)
            stats.dirs += 1
            child_cats = self._scan_dir(child, full, depth + 1)
            node.children.append(child)
            node.size += child.size
            node.files += child.files
            node.dirs += 1 + child.dirs
            for cat, val in child_cats.items():
                cat_sizes[cat] += val

        node.children.sort(key=lambda c: c.size, reverse=True)
        if cat_sizes:
            node.category = max(cat_sizes.items(), key=lambda kv: kv[1])[0]
        return cat_sizes


# ------------------------------------------------------------------ queries
def walk(node: Node) -> Iterator[Node]:
    """Pre-order traversal (iterative, safe for deep trees)."""
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        stack.extend(reversed(cur.children))


def largest_files(root: Node, n: int = 10) -> list[Node]:
    import heapq

    return heapq.nlargest(n, (x for x in walk(root) if not x.is_dir and not x.is_aggregate), key=lambda x: x.size)


def largest_folders(root: Node, n: int = 10) -> list[Node]:
    """Folders ranked by the bytes of files placed directly inside them."""
    import heapq

    return heapq.nlargest(n, (x for x in walk(root) if x.is_dir and x is not root and x.own_size > 0), key=lambda x: x.own_size)


def search(root: Node, text: str, category: str | None = None, limit: int = 1000) -> list[Node]:
    """Case-insensitive name search below ``root`` (root itself excluded)."""
    needle = text.casefold()
    out: list[Node] = []
    for n in walk(root):
        if n is root or n.is_aggregate:
            continue
        if needle and needle not in n.name.casefold():
            continue
        if category and n.category != category:
            continue
        out.append(n)
        if len(out) >= limit:
            break
    out.sort(key=lambda x: x.size, reverse=True)
    return out
