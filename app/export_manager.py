"""CSV / JSON export of a finished scan. Writes only to the file the user chose."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app import __version__
from app.scanner import Node, ScanStats, walk

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection from hostile file names."""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


def export_csv(root: Node, path: str | Path) -> int:
    """Write every retained node. Returns the number of rows written."""
    rows = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["path", "name", "type", "category", "size_bytes", "files"])
        for node in walk(root):
            kind = "folder" if node.is_dir else ("aggregate" if node.is_aggregate else "file")
            writer.writerow([_safe_cell(node.path), _safe_cell(node.name), kind, node.category, node.size, node.files])
            rows += 1
    return rows


def _node_dict(node: Node, depth: int, max_depth: int | None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": node.name,
        "type": "folder" if node.is_dir else ("aggregate" if node.is_aggregate else "file"),
        "size": node.size,
        "category": node.category,
    }
    if node.is_dir:
        d["files"] = node.files
        if max_depth is None or depth < max_depth:
            d["children"] = [_node_dict(c, depth + 1, max_depth) for c in node.children]
        elif node.children:
            d["children_truncated"] = True
    return d


def export_json(root: Node, stats: ScanStats | None, path: str | Path, max_depth: int | None = 8) -> None:
    payload: dict[str, Any] = {
        "generator": f"Disk Analyzer {__version__}",
        "root": root.path,
        "summary": {
            "total_size": root.size,
            "files": root.files,
            "folders": root.dirs,
        },
        "tree": _node_dict(root, 0, max_depth),
    }
    if stats is not None:
        payload["summary"].update(
            {
                "elapsed_seconds": round(stats.elapsed, 3),
                "inaccessible_items": stats.error_count,
                "links_skipped": stats.skipped_links,
                "categories": dict(stats.cat_sizes),
            }
        )
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
