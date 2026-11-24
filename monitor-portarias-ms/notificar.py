from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_notification(matches: list[dict], settings: dict) -> None:
    host = os.getenv("SMTP_HOST", settings.get("smtp_host", ""))
    port = int(os.getenv("SMTP_PORT") or settings.get("smtp_port", 587))
    username = os.getenv("SMTP_USER", settings.get("smtp_user", ""))
    password = os.getenv("SMTP_PASSWORD", settings.get("smtp_password", ""))
    sender = os.getenv("EMAIL_FROM", settings.get("from", username))
    recipient = os.getenv("EMAIL_TO", settings.get("to", ""))
    if not all((host, sender, recipient)):
        raise ValueError("E-mail habilitado, mas SMTP_HOST, EMAIL_FROM e EMAIL_TO precisam estar configurados.")

    message = EmailMessage()
    message["Subject"] = f"{len(matches)} ato(s) relevante(s) para Contagem/MG"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "\n\n".join(
            f"{item['number']} — {item['date']}\n{item['title']}\n"
            f"Tipo: {item['type']} | Valor: {item['value'] or 'não identificado'}\n"
            f"Trecho: {item['snippet']}\n{item['url']}"
            for item in matches
        )
    )
    logger.info("Enviando notificação para %s", recipient)
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        if username:
            server.login(username, password)
        server.send_message(message)
