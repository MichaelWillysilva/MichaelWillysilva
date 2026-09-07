#!/usr/bin/env python3
"""
make_ascii_svg.py

Turns a plain-text ASCII-art grid into a self-typing, monochrome SVG.
Each row wipes in left-to-right (a small "cursor" block rides the wipe
edge), staggered top to bottom. It prints once and freezes -- no loop.

This is the same GitHub-safe trick as the article: GitHub strips <script>
and most inline CSS from READMEs, but it *does* render SMIL/CSS animation
inside an <img>-embedded SVG.

Usage:
    python scripts/make_ascii_svg.py ascii_art/anonymous.txt avi-ascii.svg

If you later want to use a real photo instead of hand-drawn ASCII art,
run prep_photo.py first, feed its output through your own
image-to-ASCII conversion, save the resulting character grid as a .txt
file, and point this script at it -- the SVG/animation logic below
doesn't change.
"""
import sys
from pathlib import Path

FONT_SIZE = 14
LINE_HEIGHT = FONT_SIZE * 1.0
CHAR_WIDTH = FONT_SIZE * 0.6  # monospace advance width, Courier-ish
FILL_COLOR = "#c9d1d9"        # single light-gray fill -- monochrome, not rainbow
BG_COLOR = "#0d1117"          # GitHub dark-mode background
ROW_DUR = 0.5                 # seconds per row wipe
ROW_STAGGER = 0.045           # seconds between each row's start


def build_svg(rows: list[str]) -> str:
    max_len = max((len(r) for r in rows), default=0)
    width = max_len * CHAR_WIDTH + 20
    height = len(rows) * LINE_HEIGHT + 20

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG_COLOR}"/>')
    parts.append(
        f'<style>text{{font-family:"SFMono-Regular",Consolas,'
        f'"Liberation Mono",Menlo,monospace;font-size:{FONT_SIZE}px;'
        f'white-space:pre;}}</style>'
    )

    for i, row in enumerate(rows):
        if not row.strip():
            continue
        y = 10 + (i + 1) * LINE_HEIGHT - 4
        row_width = len(row) * CHAR_WIDTH
        begin = i * ROW_STAGGER
        clip_id = f"clip{i}"

        # Clip rect that grows from 0 -> full row width, then freezes.
        parts.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="10" y="{y - FONT_SIZE:.1f}" width="0" height="{FONT_SIZE * 1.4:.1f}">'
            f'<animate attributeName="width" from="0" to="{row_width:.1f}" '
            f'dur="{ROW_DUR}s" begin="{begin:.3f}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            f'</rect></clipPath>'
        )
        escaped = (
            row.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        parts.append(
            f'<text x="10" y="{y:.1f}" fill="{FILL_COLOR}" '
            f'clip-path="url(#{clip_id})">{escaped}</text>'
        )
        # Small "cursor" block that rides the wipe edge, then vanishes.
        parts.append(
            f'<rect width="{CHAR_WIDTH:.1f}" height="{FONT_SIZE * 1.2:.1f}" '
            f'fill="{FILL_COLOR}" opacity="0.85">'
            f'<animate attributeName="x" from="10" to="{10 + row_width:.1f}" '
            f'dur="{ROW_DUR}s" begin="{begin:.3f}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            f'<animate attributeName="y" from="{y - FONT_SIZE:.1f}" to="{y - FONT_SIZE:.1f}" '
            f'dur="0.01s" begin="{begin:.3f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="0.85" to="0" '
            f'dur="0.15s" begin="{begin + ROW_DUR:.3f}s" fill="freeze"/>'
            f'</rect>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ascii_art/anonymous.txt")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("avi-ascii.svg")

    rows = src.read_text(encoding="utf-8").splitlines()
    svg = build_svg(rows)
    dst.write_text(svg, encoding="utf-8")
    print(f"wrote {dst} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
