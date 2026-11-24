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
    pending = database.pending_notifications()
    assert len(pending) == 1
    assert pending[0][0] == "key-1"
    assert pending[0][1]["matched"] is True
    assert pending[0][1]["number"] == match["number"]
    assert pending[0][1]["source"] == "DOU"

    database.mark_notifications_sent(["key-1"])
    assert database.pending_notifications() == []
    database.close()


def test_unmatched_new_documents_are_pending_notifications(tmp_path):
    database = Database(tmp_path / "test.db")
    database.save_document(
        key="key-2",
        source="Anvisa",
        number="RDC 123",
        published="2026-11-24",
        title="Nova regra sanitária",
        ementa="Regra aplicável a serviços de saúde.",
        url="https://example.org/rdc-123",
        text_hash="sha256",
        match=None,
        email_pending=True,
    )

    pending = database.pending_notifications()
    assert len(pending) == 1
    assert pending[0][0] == "key-2"
    assert pending[0][1]["matched"] is False
    assert pending[0][1]["source"] == "Anvisa"
    assert pending[0][1]["ementa"] == "Regra aplicável a serviços de saúde."

    database.mark_notifications_sent(["key-2"])
    assert database.pending_notifications() == []
    database.close()
