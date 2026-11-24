from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_notification(items: list[dict], settings: dict) -> None:
    host = os.getenv("SMTP_HOST", settings.get("smtp_host", ""))
    port = int(os.getenv("SMTP_PORT") or settings.get("smtp_port", 587))
    username = os.getenv("SMTP_USER", settings.get("smtp_user", ""))
    password = os.getenv("SMTP_PASSWORD", settings.get("smtp_password", ""))
    sender = os.getenv("EMAIL_FROM") or settings.get("from") or username
    recipient = os.getenv("EMAIL_TO", settings.get("to", ""))
    if not all((host, sender, recipient)):
        raise ValueError("E-mail habilitado, mas SMTP_HOST, EMAIL_FROM e EMAIL_TO precisam estar configurados.")

    message = EmailMessage()
    subject = (
        "nova publicação de saúde monitorada"
        if len(items) == 1
        else "novas publicações de saúde monitoradas"
    )
    message["Subject"] = f"{len(items)} {subject}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "\n\n".join(
            "\n".join(
                (
                    f"{item.get('number') or 'Número não identificado'} — "
                    f"{item.get('date') or 'Data não identificada'}",
                    f"Fonte: {item.get('source') or 'não identificada'}",
                    f"Órgão: {item.get('agency') or 'não identificado'}",
                    f"Ementa: {item.get('ementa') or item.get('title') or 'não disponível'}",
                    f"Tipo: {item.get('type') or 'não classificado'} | "
                    f"Tema: {', '.join(item.get('theme', [])) or 'não classificado'}",
                    f"Relevância para Contagem: {item.get('relevance') or 'não classificada'}",
                    f"Valor: {item.get('value') or 'não identificado'} | "
                    f"Prazo: {item.get('deadline') or 'não identificado'}",
                    f"Menções: {', '.join(item.get('municipal_mentions', [])) or 'não identificadas'}",
                    f"Trecho: {item.get('snippet') or item.get('ementa') or 'não disponível'}",
                    f"Correspondência direta com Contagem: "
                    f"{'sim' if item.get('matched') else 'não identificada'}",
                    f"Link: {item.get('url') or 'não disponível'}",
                )
            )
            for item in items
        )
    )
    logger.info("Enviando digest com %d novas publicações.", len(items))
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        if username:
            server.login(username, password)
        server.send_message(message)
