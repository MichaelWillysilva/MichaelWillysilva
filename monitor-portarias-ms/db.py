from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS portarias (
                document_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                number TEXT NOT NULL,
                published TEXT NOT NULL,
                title TEXT NOT NULL,
                ementa TEXT NOT NULL,
                url TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                matched INTEGER NOT NULL DEFAULT 0,
                match_json TEXT,
                email_sent INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_portarias_published ON portarias(published);
            """
        )
        columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(portarias)")
        }
        migrations = {
            "agency": "TEXT NOT NULL DEFAULT ''",
            "act_type": "TEXT NOT NULL DEFAULT ''",
            "theme": "TEXT NOT NULL DEFAULT ''",
            "relevance": "TEXT NOT NULL DEFAULT ''",
            "amount": "TEXT NOT NULL DEFAULT ''",
            "deadline": "TEXT NOT NULL DEFAULT ''",
            "municipal_mentions": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, definition in migrations.items():
            if column not in columns:
                self.connection.execute(
                    f"ALTER TABLE portarias ADD COLUMN {column} {definition}"
                )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_portarias_relevance ON portarias(relevance)"
        )
        self.connection.commit()

    def has_seen(self, key: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM portarias WHERE document_key = ?", (key,)
        ).fetchone() is not None

    def save_document(
        self,
        *,
        key: str,
        source: str,
        number: str,
        published: str,
        title: str,
        ementa: str,
        url: str,
        text_hash: str,
        match: dict | None,
        email_pending: bool = False,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO portarias
                (document_key, source, number, published, title, ementa, url, text_hash,
                 matched, match_json, email_sent, agency, act_type, theme, relevance,
                 amount, deadline, municipal_mentions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                source,
                number or "",
                published or "",
                title or "",
                ementa or "",
                url,
                text_hash,
                int(match is not None),
                json.dumps(match, ensure_ascii=False) if match else None,
                int(not email_pending),
                match.get("agency", "") if match else "",
                match.get("type", "") if match else "",
                json.dumps(match.get("theme", []), ensure_ascii=False) if match else "",
                match.get("relevance", "") if match else "",
                match.get("value", "") if match else "",
                match.get("deadline", "") if match else "",
                json.dumps(match.get("municipal_mentions", []), ensure_ascii=False)
                if match
                else "[]",
            ),
        )
        self.connection.commit()

    def all_matches(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT match_json FROM portarias WHERE matched = 1 ORDER BY published, number"
        ).fetchall()
        return [json.loads(row[0]) for row in rows if row[0]]

    def pending_notifications(self) -> list[tuple[str, dict]]:
        rows = self.connection.execute(
            "SELECT document_key, match_json FROM portarias "
            "WHERE matched = 1 AND email_sent = 0"
        ).fetchall()
        return [(row[0], json.loads(row[1])) for row in rows if row[1]]

    def mark_notifications_sent(self, keys: list[str]) -> None:
        self.connection.executemany(
            "UPDATE portarias SET email_sent = 1 WHERE document_key = ?",
            ((key,) for key in keys),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
