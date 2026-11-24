from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_site_data(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "records": records,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
