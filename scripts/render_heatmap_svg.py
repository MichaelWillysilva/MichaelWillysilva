#!/usr/bin/env python3
"""
render_heatmap_svg.py

Renders data/contributions.json as the classic 53-week x 7-day grid of
rounded, colored boxes, using a GitHub-ish green ramp. Reveals once with
a diagonal, line-after-line slide-down (plain CSS @keyframes -- GitHub
runs those inside an embedded SVG same as SMIL), then freezes. Adds a
Less -> More legend and a stats footer line.

Usage:
    python scripts/render_heatmap_svg.py
"""
import json
from pathlib import Path

SRC = Path("data/contributions.json")
DST = Path("contrib-heatmap.svg")

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
# none -> brightest (level 5 is a neon top end, used for exceptional days)

CELL = 11
GAP = 3
LEFT_PAD = 30
TOP_PAD = 20
BOTTOM_PAD = 34
STAGGER = 0.012


def level_color(level, count):
    if level is not None:
        return PALETTE[min(level, len(PALETTE) - 1)]
    # fall back to count-based bucketing if data-level wasn't present
    if not count:
        return PALETTE[0]
    if count < 3:
        return PALETTE[1]
    if count < 6:
        return PALETTE[2]
    if count < 10:
        return PALETTE[3]
    return PALETTE[4]


def build_svg(payload: dict) -> str:
    days = payload.get("days", [])
    stats = payload.get("stats", {})
    username = payload.get("username", "")

    # bucket into 53 columns x 7 rows, oldest first
    weeks: list[list[dict]] = []
    if days:
        week: list[dict] = []
        for d in days:
            week.append(d)
            if len(week) == 7:
                weeks.append(week)
                week = []
        if week:
            weeks.append(week)

    n_weeks = max(len(weeks), 53)
    width = LEFT_PAD + n_weeks * (CELL + GAP) + 20
    height = TOP_PAD + 7 * (CELL + GAP) + BOTTOM_PAD

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
        f'<style>'
        f'text{{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;'
        f'font-size:11px;fill:#8b949e;}}'
        f'.cell{{opacity:0;animation:reveal 0.35s ease-out forwards;}}'
        f'@keyframes reveal{{from{{opacity:0;transform:translateY(-4px);}}'
        f'to{{opacity:1;transform:translateY(0);}}}}'
        f'</style>',
        f'<rect width="100%" height="100%" fill="#0d1117"/>',
    ]

    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            x = LEFT_PAD + wi * (CELL + GAP)
            y = TOP_PAD + di * (CELL + GAP)
            color = level_color(day.get("level"), day.get("count"))
            delay = (wi + di) * STAGGER
            parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{color}" style="animation-delay:{delay:.3f}s" '
                f'transform-origin="{x + CELL / 2} {y + CELL / 2}">'
                f'<title>{day.get("date", "")}: {day.get("count", 0)} contributions</title>'
                f"</rect>"
            )

    # legend, bottom-left
    legend_y = TOP_PAD + 7 * (CELL + GAP) + 18
    parts.append(f'<text x="{LEFT_PAD}" y="{legend_y}">Less</text>')
    lx = LEFT_PAD + 32
    for color in PALETTE[:-1]:  # skip the neon top tier in the legend
        parts.append(f'<rect x="{lx}" y="{legend_y - 9}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"/>')
        lx += CELL + GAP
    parts.append(f'<text x="{lx + 4}" y="{legend_y}">More</text>')

    total = stats.get("total_last_year")
    if total is not None:
        footer = f"{total:,} contributions in the last year"
        if username:
            footer += f"  ·  @{username}"
        parts.append(
            f'<text x="{width - 20}" y="{legend_y}" text-anchor="end">{footer}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main():
    if not SRC.exists():
        raise SystemExit(f"{SRC} not found -- run fetch_contributions.py first")
    payload = json.loads(SRC.read_text(encoding="utf-8"))
    DST.write_text(build_svg(payload), encoding="utf-8")
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
