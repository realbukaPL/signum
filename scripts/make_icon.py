"""Generuje ikonę aplikacji (signum.ico + signum.png) — stylizowany podpis.

Uruchamiane ręcznie przy zmianie identyfikacji wizualnej:
    python scripts/make_icon.py
"""

from __future__ import annotations

import math
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parents[1] / "src" / "signum" / "ui" / "resources"
SIZES = [256, 128, 64, 48, 32, 16]

BG = (26, 35, 126)  # granat
INK = (255, 255, 255)  # biały "podpis"
ACCENT = (255, 179, 0)  # bursztynowa kropka


def draw_base(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = size * 0.22
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=BG)

    # Stylizowany zamaszysty podpis: pętla + ogonek.
    cx, cy = size * 0.5, size * 0.52
    points = []
    for i in range(200):
        t = i / 199
        angle = t * math.pi * 2.4 - math.pi * 0.7
        r = size * (0.30 - 0.16 * t)
        x = cx + math.cos(angle) * r * 1.15 + t * size * 0.16
        y = cy + math.sin(angle) * r * 0.62
        points.append((x, y))
    width = max(2, size // 18)
    for a, b in pairwise(points):
        d.line([a, b], fill=INK, width=width)
    for p in points[:: len(points) - 1]:  # zaokrąglone końce
        d.ellipse(
            (p[0] - width / 2, p[1] - width / 2, p[0] + width / 2, p[1] + width / 2), fill=INK
        )

    # Linia podpisu i kropka
    line_y = size * 0.80
    d.line([(size * 0.16, line_y), (size * 0.84, line_y)], fill=INK, width=max(1, size // 42))
    dot_r = size * 0.045
    d.ellipse(
        (size * 0.78 - dot_r, size * 0.60 - dot_r, size * 0.78 + dot_r, size * 0.60 + dot_r),
        fill=ACCENT,
    )
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = draw_base(256)
    base.save(OUT_DIR / "signum.png")
    base.save(
        OUT_DIR / "signum.ico",
        sizes=[(s, s) for s in SIZES],
    )
    print(f"Zapisano ikony w {OUT_DIR}")


if __name__ == "__main__":
    main()
