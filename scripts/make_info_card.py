#!/usr/bin/env python3
"""
make_info_card.py

Hand-authors a small neofetch-style SVG panel: a title bar, then colored
key/value rows. Each line fades + slides in on a short stagger so it looks
like it's printing next to the ASCII portrait.

Set STATIC=1 to emit a frozen (already-revealed) frame, useful for local
Quick Look previews where SMIL doesn't animate.

Edit the FIELDS list below with your own info, then run:
    python scripts/make_info_card.py
"""
import os
import sys
from pathlib import Path

USERNAME = "MichaelWillysilva"
TITLE = f"{USERNAME.lower()}@github"

# key, value, accent hex color
FIELDS = [
    ("OS",         "Anonymous // Unix-like",        "#79c0ff"),
    ("Now",        "Building things, staying low-key", "#7ee787"),
    ("Prev",       "-- edit me --",                  "#d2a8ff"),
    ("Stack",      "-- edit me: e.g. JS/TS, Python --", "#ffa657"),
    ("Highlights", "-- edit me --",                  "#f778ba"),
    ("Shell",      "we-are-legion",                  "#a5d6ff"),
]

FONT_SIZE = 15
LINE_HEIGHT = FONT_SIZE * 1.8
PAD = 24
KEY_COLOR = "#8b949e"
VALUE_COLOR = "#c9d1d9"
BG = "#0d1117"
BORDER = "#30363d"
TITLE_BAR_H = 40
ROW_STAGGER = 0.18
FADE_DUR = 0.45


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(static: bool) -> str:
    key_col_w = max(len(k) for k, _, _ in FIELDS) * (FONT_SIZE * 0.62) + 4
    width = 490
    height = TITLE_BAR_H + PAD + len(FIELDS) * LINE_HEIGHT + PAD

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height:.0f}" '
        f'width="{width}" height="{height:.0f}">',
        f'<style>text{{font-family:"SFMono-Regular",Consolas,'
        f'"Liberation Mono",Menlo,monospace;}}</style>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1:.0f}" '
        f'rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{TITLE_BAR_H}" '
        f'rx="10" fill="#161b22"/>',
        f'<rect x="0.5" y="{TITLE_BAR_H / 2:.0f}" width="{width - 1}" '
        f'height="{TITLE_BAR_H / 2:.0f}" fill="#161b22"/>',
        f'<circle cx="24" cy="{TITLE_BAR_H / 2:.0f}" r="6" fill="#ff5f56"/>',
        f'<circle cx="44" cy="{TITLE_BAR_H / 2:.0f}" r="6" fill="#ffbd2e"/>',
        f'<circle cx="64" cy="{TITLE_BAR_H / 2:.0f}" r="6" fill="#27c93f"/>',
        f'<text x="{width / 2}" y="{TITLE_BAR_H / 2 + 5:.0f}" text-anchor="middle" '
        f'font-size="{FONT_SIZE}" fill="{VALUE_COLOR}">{esc(TITLE)}</text>',
    ]

    for i, (key, value, accent) in enumerate(FIELDS):
        y = TITLE_BAR_H + PAD + (i + 1) * LINE_HEIGHT - LINE_HEIGHT / 2 + FONT_SIZE / 3
        begin = i * ROW_STAGGER

        group_attrs = 'opacity="1"' if static else 'opacity="0"'
        transform_start = "" if static else ' transform="translate(-10,0)"'

        parts.append(f'<g {group_attrs}{transform_start}>')
        if not static:
            parts.append(
                f'<animate attributeName="opacity" from="0" to="1" '
                f'dur="{FADE_DUR}s" begin="{begin:.3f}s" fill="freeze"/>'
            )
            parts.append(
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="-10 0" to="0 0" dur="{FADE_DUR}s" begin="{begin:.3f}s" fill="freeze"/>'
            )
        parts.append(
            f'<text x="{PAD}" y="{y:.1f}" font-size="{FONT_SIZE}" '
            f'font-weight="bold" fill="{accent}">{esc(key)}</text>'
        )
        parts.append(
            f'<text x="{PAD + key_col_w:.1f}" y="{y:.1f}" font-size="{FONT_SIZE}" '
            f'fill="{VALUE_COLOR}">{esc(value)}</text>'
        )
        parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


def main():
    static = os.environ.get("STATIC") == "1"
    dst = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("info-card.svg")
    dst.write_text(build_svg(static), encoding="utf-8")
    print(f"wrote {dst} (static={static})")


if __name__ == "__main__":
    main()
