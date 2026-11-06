"""Generate assets/icon.png, icon.ico, icon.icns (requires Pillow)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets"
BLOCKS = [  # x0, y0, x1, y1 in a 0..100 grid, colour
    (0, 0, 58, 55, "#E4572E"),
    (58, 0, 100, 34, "#9B5DE5"),
    (58, 34, 100, 55, "#F29E4C"),
    (0, 55, 36, 100, "#4C8DFF"),
    (36, 55, 70, 100, "#43AA8B"),
    (70, 55, 100, 78, "#2EC4B6"),
    (70, 78, 100, 100, "#F15BB5"),
]


def render(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.22), fill="#000000")
    pad = int(size * 0.14)
    inner = size - 2 * pad
    gap = max(2, int(size * 0.012))
    for x0, y0, x1, y1, col in BLOCKS:
        box = (
            pad + x0 * inner / 100 + gap,
            pad + y0 * inner / 100 + gap,
            pad + x1 * inner / 100 - gap,
            pad + y1 * inner / 100 - gap,
        )
        d.rounded_rectangle(box, radius=int(size * 0.03), fill=col)
    return img


def main() -> None:
    OUT.mkdir(exist_ok=True)
    base = render(1024)
    base.resize((512, 512), Image.Resampling.LANCZOS).save(OUT / "icon.png")
    base.save(OUT / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    base.save(OUT / "icon.icns")
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
