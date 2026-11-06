import random

import pytest

from app.scanner import Node, Scanner
from app.treemap import build_tiles, squarify, tile_at


def test_squarify_fills_area_without_overlap():
    random.seed(1)
    values = sorted((random.randint(1, 1000) for _ in range(60)), reverse=True)
    rects = squarify([float(v) for v in values], 0, 0, 800, 500)
    assert len(rects) == 60
    assert sum(r.area for r in rects) == pytest.approx(800 * 500, rel=1e-6)
    for r in rects:
        assert r.x >= -1e-6 and r.y >= -1e-6
        assert r.x + r.w <= 800 + 1e-6 and r.y + r.h <= 500 + 1e-6
    for i, a in enumerate(rects):  # no pairwise overlap
        for b in rects[i + 1 :]:
            ox = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
            oy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
            assert not (ox > 1e-6 and oy > 1e-6)


def test_squarify_areas_proportional():
    rects = squarify([60.0, 30.0, 10.0], 0, 0, 100, 100)
    assert [round(r.area) for r in rects] == [6000, 3000, 1000]


def test_squarify_edge_cases():
    assert squarify([], 0, 0, 10, 10) == []
    assert all(r.area == 0 for r in squarify([1.0, 1.0], 0, 0, 0, 10))


def test_build_tiles_nested(sample_tree):
    root = Scanner().scan(sample_tree)
    tiles = build_tiles(root, 1000, 600, min_expand=10)
    names = [t.node.name for t in tiles]
    assert {"movie.mp4", "a", "doc.pdf", "c.py"} <= set(names)
    # parents precede children
    assert names.index("a") < names.index("doc.pdf") < len(names)
    top = [t for t in tiles if t.depth == 0]
    assert sum(t.rect.area for t in top) == pytest.approx(1000 * 600, rel=1e-6)
    doc = next(t for t in tiles if t.node.name == "doc.pdf")
    assert doc.top.name == "a"


def test_tile_at_returns_deepest(sample_tree):
    root = Scanner().scan(sample_tree)
    tiles = build_tiles(root, 1000, 600, min_expand=10)
    doc = next(t for t in tiles if t.node.name == "doc.pdf")
    cx, cy = doc.rect.x + doc.rect.w / 2, doc.rect.y + doc.rect.h / 2
    hit = tile_at(tiles, cx, cy)
    assert hit is not None and hit.node.name == "doc.pdf"
    assert tile_at(tiles, -5, -5) is None


def test_tiles_empty_and_capped():
    assert build_tiles(Node("r", True), 100, 100) == []
    root = Node("r", True)
    root.children = [Node(f"f{i}", False, size=i + 1, parent=root) for i in range(500)]
    assert len(build_tiles(root, 4000, 4000, max_tiles=50)) == 50
