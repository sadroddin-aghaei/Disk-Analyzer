import csv
import json

from app import __version__
from app.export_manager import export_csv, export_json
from app.scanner import Scanner


def test_csv_export(sample_tree, tmp_path):
    root = Scanner().scan(sample_tree)
    out = tmp_path / "out.csv"
    rows = export_csv(root, out)
    with open(out, newline="", encoding="utf-8-sig") as fh:
        data = list(csv.DictReader(fh))
    assert len(data) == rows
    assert data[0]["type"] == "folder" and int(data[0]["size_bytes"]) == 7110
    movie = next(r for r in data if r["name"] == "movie.mp4")
    assert movie["category"] == "video" and movie["size_bytes"] == "5000" and movie["type"] == "file"


def test_csv_formula_injection_is_neutralised(tmp_path):
    base = tmp_path / "scan"
    base.mkdir()
    (base / "=cmd.txt").write_bytes(b"x")
    root = Scanner().scan(base)
    out = tmp_path / "o.csv"
    export_csv(root, out)
    text = out.read_text(encoding="utf-8-sig")
    assert "'=cmd.txt" in text


def test_csv_persian_names_roundtrip(tmp_path):
    base = tmp_path / "scan"
    base.mkdir()
    (base / "گزارش سالانه.pdf").write_bytes(b"x" * 7)
    out = tmp_path / "fa.csv"
    export_csv(Scanner().scan(base), out)
    assert "گزارش سالانه.pdf" in out.read_text(encoding="utf-8-sig")


def test_json_export(sample_tree, tmp_path):
    sc = Scanner()
    root = sc.scan(sample_tree)
    out = tmp_path / "out.json"
    export_json(root, sc.stats, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["generator"] == f"Disk Analyzer {__version__}"
    assert data["summary"]["total_size"] == 7110
    assert data["summary"]["files"] == 4
    assert data["tree"]["children"][0]["name"] == "movie.mp4"


def test_json_depth_limit(sample_tree, tmp_path):
    root = Scanner().scan(sample_tree)
    out = tmp_path / "d.json"
    export_json(root, None, out, max_depth=0)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "children" not in data["tree"] and data["tree"]["children_truncated"] is True
