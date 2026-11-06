"""Background scan worker: runs the Scanner on a thread pool, reports via Qt signals."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal

from app.scanner import ScanCancelledError, Scanner, ScanStats


class ScanWorker(QObject):
    progress = Signal(int, int, int, str)  # files, dirs, bytes, current path
    finished = Signal(object, object)  # Node, ScanStats
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._scanner = Scanner(self._on_progress)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="disk-scan")
        self._future: Future[None] | None = None

    def start(self) -> None:
        self._future = self._executor.submit(self._run)

    def cancel(self) -> None:
        self._scanner.cancel()

    def shutdown(self) -> None:
        self._scanner.cancel()
        self._executor.shutdown(wait=True)

    def _on_progress(self, stats: ScanStats, path: str) -> None:
        self.progress.emit(stats.files, stats.dirs, stats.bytes, path)

    def _run(self) -> None:
        try:
            root = self._scanner.scan(self._path)
        except ScanCancelledError:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(f"{exc.__class__.__name__}: {exc}")
        else:
            self.finished.emit(root, self._scanner.stats)
