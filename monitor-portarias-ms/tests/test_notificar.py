import os
from unittest.mock import patch

from notificar import send_notification


def test_digest_includes_new_publications_without_contagem_match():
    item = {
        "source": "Anvisa",
        "number": "RDC 123",
        "date": "2026-11-24",
        "title": "Nova regra sanitária",
        "ementa": "Regra aplicável a serviços de saúde.",
        "url": "https://example.org/rdc-123",
        "matched": False,
    }

    with (
        patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.example.test",
                "SMTP_PORT": "587",
                "SMTP_USER": "",
                "SMTP_PASSWORD": "",
                "EMAIL_FROM": "sender@example.test",
                "EMAIL_TO": "recipient@example.test",
            },
        ),
        patch("notificar.smtplib.SMTP") as smtp_factory,
    ):
        server = smtp_factory.return_value.__enter__.return_value
        send_notification([item], {})

    message = server.send_message.call_args.args[0]
    body = message.get_content()
    assert "1 nova publicação de saúde monitorada" in message["Subject"]
    assert "Anvisa" in body
    assert "Correspondência direta com Contagem: não identificada" in body
    assert item["url"] in body
