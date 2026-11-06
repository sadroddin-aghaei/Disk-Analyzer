"""Pure-Python squarified treemap layout (no Qt dependency, fully testable)."""

from __future__ import annotations

from dataclasses import dataclass

from app.scanner import Node

HEADER_HEIGHT = 16.0
PADDING = 2.0
MIN_TILE = 1.5


@dataclass(slots=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h

    @property
    def area(self) -> float:
        return self.w * self.h


@dataclass(eq=False, slots=True)
class Tile:
    node: Node
    rect: Rect
    depth: int
    top: Node  # the depth-0 ancestor (navigation target)
    header: float = 0.0
    container: bool = False


def _worst(row: list[float], side: float) -> float:
    s = sum(row)
    if s <= 0 or side <= 0:
        return float("inf")
    return max(max(side * side * r / (s * s), (s * s) / (side * side * r)) for r in row)


def squarify(values: list[float], x: float, y: float, w: float, h: float) -> list[Rect]:
    """Squarified treemap (Bruls et al.). ``values`` must be positive, sorted descending."""
    n = len(values)
    total = sum(values)
    if n == 0:
        return []
    if total <= 0 or w <= 0 or h <= 0:
        return [Rect(x, y, 0.0, 0.0) for _ in values]

    scale = w * h / total
    areas = [v * scale for v in values]
    rects: list[Rect] = []
    i = 0
    while i < n:
        side = min(w, h)
        row = [areas[i]]
        j = i + 1
        while j < n and _worst([*row, areas[j]], side) <= _worst(row, side):
            row.append(areas[j])
            j += 1
        s = sum(row)
        if w >= h:  # column on the left
            cw = s / h
            cy = y
            for a in row:
                rh = a / cw if cw > 0 else 0.0
                rects.append(Rect(x, cy, cw, rh))
                cy += rh
            x += cw
            w -= cw
        else:  # row on top
            rh = s / w
            cx = x
            for a in row:
                rw = a / rh if rh > 0 else 0.0
                rects.append(Rect(cx, y, rw, rh))
                cx += rw
            y += rh
            h -= rh
        i = j
    return rects


def build_tiles(
    root: Node, width: float, height: float, *, max_depth: int = 3, min_expand: float = 44.0, max_tiles: int = 8000
) -> list[Tile]:
    """Lay out the children of ``root`` (nested for folders) inside width x height.

    Parents are always emitted before their children, so the *last* tile that
    contains a point is the deepest one.
    """
    tiles: list[Tile] = []

    def rec(node: Node, x: float, y: float, w: float, h: float, depth: int, top: Node | None) -> None:
        kids = sorted((c for c in node.children if c.size > 0), key=lambda c: c.size, reverse=True)
        if not kids or w <= 0 or h <= 0:
            return
        rects = squarify([float(c.size) for c in kids], x, y, w, h)
        for child, r in zip(kids, rects, strict=True):
            if r.w < MIN_TILE or r.h < MIN_TILE or len(tiles) >= max_tiles:
                continue
            tile = Tile(child, r, depth, top if top is not None else child)
            tiles.append(tile)
            if child.is_dir and depth < max_depth - 1 and r.w >= min_expand and r.h >= min_expand:
                header = HEADER_HEIGHT if (r.h >= HEADER_HEIGHT + 28 and r.w >= 64) else 0.0
                tile.header = header
                before = len(tiles)
                rec(
                    child,
                    r.x + PADDING,
                    r.y + PADDING + header,
                    r.w - 2 * PADDING,
                    r.h - 2 * PADDING - header,
                    depth + 1,
                    tile.top,
                )
                tile.container = len(tiles) > before

    rec(root, 0.0, 0.0, float(width), float(height), 0, None)
    return tiles


def tile_at(tiles: list[Tile], px: float, py: float) -> Tile | None:
    for tile in reversed(tiles):
        if tile.rect.contains(px, py):
            return tile
    return None
