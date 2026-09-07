#!/usr/bin/env python3
"""
fetch_contributions.py

GitHub serves your contribution calendar as a public HTML fragment at
https://github.com/users/<username>/contributions -- the same markup the
profile page itself uses. No GraphQL, no personal access token needed.

Writes data/contributions.json with the raw per-day counts plus a few
derived stats (current streak, longest streak, best day, monthly totals)
that render_heatmap_svg.py consumes.

Usage:
    python scripts/fetch_contributions.py [username]
"""
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "MichaelWillysilva"
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT = Path("data/contributions.json")


def fetch_days(username: str) -> list[dict]:
    resp = requests.get(
        f"https://github.com/users/{username}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (profile-readme-bot)"},
        timeout=20,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    days = []
    # GitHub renders each day as a <td> (older markup) or <rect>/<td> with
    # data-date + data-level (or a "tooltip" style with the count in text).
    cells = soup.select("td.ContributionCalendar-day") or soup.select("rect.ContributionCalendar-day")
    for cell in cells:
        d = cell.get("data-date")
        if not d:
            continue
        level = cell.get("data-level")
        count_attr = cell.get("data-count")
        days.append(
            {
                "date": d,
                "level": int(level) if level is not None else None,
                "count": int(count_attr) if count_attr is not None else None,
            }
        )
    return days


def derive_stats(days: list[dict]) -> dict:
    days_sorted = sorted(days, key=lambda d: d["date"])
    counts = [d["count"] or 0 for d in days_sorted]

    total = sum(counts)

    # streaks
    longest = current = 0
    running = 0
    today = date.today().isoformat()
    for d in days_sorted:
        c = d["count"] or 0
        if c > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    # current streak: walk backward from the most recent day with data
    running = 0
    for d in reversed(days_sorted):
        c = d["count"] or 0
        if c > 0:
            running += 1
        else:
            if d["date"] != today:
                break
    current = running

    best_day = max(days_sorted, key=lambda d: d["count"] or 0, default=None)

    monthly = defaultdict(int)
    for d in days_sorted:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] += d["count"] or 0

    return {
        "total_last_year": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best_day,
        "monthly_totals": dict(sorted(monthly.items())),
    }


def main():
    days = fetch_days(USERNAME)
    if not days:
        print("warning: no contribution cells found -- GitHub markup may have "
              "changed, check the CSS selectors above", file=sys.stderr)

    payload = {
        "username": USERNAME,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "days": days,
        "stats": derive_stats(days) if days else {},
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(days)} days)")


if __name__ == "__main__":
    main()
