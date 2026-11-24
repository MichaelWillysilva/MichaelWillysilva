from db import Database


def test_seen_match_and_pending_notification_lifecycle(tmp_path):
    database = Database(tmp_path / "test.db")
    match = {"number": "123", "url": "https://example.org/123"}

    database.save_document(
        key="key-1",
        source="DOU",
        number="123",
        published="2026-11-24",
        title="Portaria",
        ementa="Habilita Contagem",
        url=match["url"],
        text_hash="sha256",
        match=match,
        email_pending=True,
    )

    assert database.has_seen("key-1")
    assert database.all_matches() == [match]
    assert database.pending_notifications() == [("key-1", match)]

    database.mark_notifications_sent(["key-1"])
    assert database.pending_notifications() == []
    database.close()
