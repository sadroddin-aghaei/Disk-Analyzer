from PySide6.QtWidgets import QApplication

from app.drive_manager import list_drives, usage_for
from app.main_window import MainWindow
from app.scanner import Scanner
from app.settings import Settings
from app.workers import ScanWorker


def test_drive_listing_has_valid_numbers():
    drives = list_drives()
    assert drives and drives[0].is_home
    for d in drives:
        assert d.total >= d.used >= 0
        assert 0 <= d.percent <= 100


def test_usage_for_missing_path_is_zero(tmp_path):
    assert usage_for(tmp_path / "nope") == (0, 0, 0)


def test_worker_scans_in_background(sample_tree):
    from PySide6.QtCore import QEventLoop, QTimer

    app = QApplication.instance() or QApplication([])
    results: list[tuple] = []
    loop = QEventLoop()
    worker = ScanWorker(str(sample_tree))

    def on_done(root, stats):
        results.append((root, stats))
        loop.quit()

    worker.finished.connect(on_done)
    worker.failed.connect(lambda _msg: loop.quit())
    QTimer.singleShot(15000, loop.quit)
    worker.start()
    loop.exec()
    worker.shutdown()
    app.processEvents()
    assert len(results) == 1
    root, stats = results[0]
    assert root.size == 7110 and stats.files == 4


def test_worker_reports_failure_for_missing_path(tmp_path):
    from PySide6.QtCore import QEventLoop, QTimer

    app = QApplication.instance() or QApplication([])
    errors: list[str] = []
    loop = QEventLoop()
    worker = ScanWorker(str(tmp_path / "does-not-exist"))

    def on_fail(msg):
        errors.append(msg)
        loop.quit()

    worker.failed.connect(on_fail)
    QTimer.singleShot(15000, loop.quit)
    worker.start()
    loop.exec()
    worker.shutdown()
    app.processEvents()
    assert errors and "FileNotFoundError" in errors[0]


def test_window_show_result_and_navigation(sample_tree):
    app = QApplication.instance() or QApplication([])
    sc = Scanner()
    root = sc.scan(sample_tree)
    win = MainWindow(Settings(), persist_settings=False)
    win.resize(1200, 760)
    win.show_result(root, sc.stats)
    win.treemap._relayout()
    assert win.treemap.tile_count >= 4
    a = next(c for c in root.children if c.name == "a")
    win.navigate(a)
    assert win.current is a and win.up_btn.isEnabled()
    win._go_up()
    assert win.current is root
    win.search_edit.setText("doc")
    win._refresh_list()
    assert win.tree.topLevelItemCount() == 1
    app.processEvents()
    win.close()
