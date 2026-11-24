from __future__ import annotations

import argparse
import hashlib
import logging
import os
import csv
from datetime import date, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

from db import Database
from filtros import classify_document
from fontes import SOURCES
from relatorio import write_report
from notificar import send_notification
from site_data import write_site_data

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "contagem_portarias.csv"
REPORT_DIR = ROOT / "relatorios"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitora atos públicos de saúde relevantes para Contagem/MG."
    )
    parser.add_argument("--desde", type=date.fromisoformat, help="Data inicial (AAAA-MM-DD).")
    parser.add_argument(
        "--fonte",
        choices=("all", *SOURCES.keys()),
        default="all",
        help="Fonte a consultar (padrão: todas).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Consulta sem gravar ou notificar.")
    return parser.parse_args()


def load_config() -> dict:
    with (ROOT / "config.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def document_key(
    source: str, url: str, number: str, published: str, title: str = ""
) -> str:
    identity = "|".join((source, url, number, published, title))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def write_csv(rows: list[dict]) -> None:
    fields = (
        "source",
        "agency",
        "number",
        "date",
        "title",
        "ementa",
        "type",
        "theme",
        "relevance",
        "value",
        "deadline",
        "municipal_mentions",
        "snippet",
        "url",
    )
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = {field: row.get(field, "") for field in fields}
            item["theme"] = ", ".join(item["theme"]) if isinstance(item["theme"], list) else item["theme"]
            item["municipal_mentions"] = (
                ", ".join(item["municipal_mentions"])
                if isinstance(item["municipal_mentions"], list)
                else item["municipal_mentions"]
            )
            writer.writerow(item)


def env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().casefold() in {"1", "true", "yes", "on"}


def run() -> int:
    load_dotenv(ROOT / ".env")
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("monitor-portarias")
    args = parse_args()
    config = load_config()
    email_enabled = bool(
        config.get("email", {}).get("enabled", False) or env_enabled("EMAIL_ENABLED")
    )
    since = args.desde or (date.today() - timedelta(days=1))
    selected = SOURCES if args.fonte == "all" else {args.fonte: SOURCES[args.fonte]}
    if args.fonte == "all":
        selected = {
            key: source
            for key, source in selected.items()
            if config.get("sources", {}).get(key, True)
        }

    matches: list[dict] = []
    failures: list[str] = []
    source_counts: dict[str, int] = {}
    completed_sources = 0
    database = None if args.dry_run else Database(ROOT / "portarias.db")
    source_stats: dict[str, dict[str, int]] = {}

    try:
        for source_key, source_class in selected.items():
            source = source_class(config)
            processed = 0
            relevant = 0
            source_errors = 0
            try:
                candidates = source.fetch_documents(since)
                completed_sources += 1
                source_warnings = getattr(source, "warnings", [])
                for warning in source_warnings:
                    failures.append(f"{source.name}: {warning}")
                    logger.warning("%s: %s", source.name, warning)
            except Exception as exc:
                message = f"{source.name}: consulta falhou: {exc}"
                logger.exception(message)
                failures.append(message)
                source_counts[source.name] = 0
                source_stats[source.name] = {
                    "fetched": 0,
                    "processed": 0,
                    "matches": 0,
                    "errors": 1,
                    "relevance": {"alta": 0, "média": 0, "baixa": 0},
                }
                continue
            source_stats[source.name] = {
                "fetched": len(candidates),
                "processed": 0,
                "matches": 0,
                "errors": len(getattr(source, "warnings", [])),
                "relevance": {"alta": 0, "média": 0, "baixa": 0},
            }

            for candidate in candidates:
                key = document_key(
                    source_key,
                    candidate.url,
                    candidate.number,
                    candidate.published,
                    candidate.title,
                )
                if database and database.has_seen(key):
                    continue
                try:
                    full_text = source.fetch_full_text(candidate)
                    text_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
                    match_data = classify_document(
                        candidate, full_text, source_key, config
                    )
                    if match_data:
                        matches.append(match_data)
                        relevant += 1
                        source_stats[source.name]["relevance"][match_data["relevance"]] += 1

                    if database:
                        database.save_document(
                            key=key,
                            source=source.name,
                            number=candidate.number,
                            published=candidate.published,
                            title=candidate.title,
                            ementa=candidate.summary,
                            url=candidate.url,
                            text_hash=text_hash,
                            match=match_data,
                            email_pending=email_enabled,
                        )
                    processed += 1
                except Exception as exc:
                    message = f"{source.name}: falha ao processar {candidate.url}: {exc}"
                    logger.exception(message)
                    failures.append(message)
                    source_errors += 1
            source_counts[source.name] = processed
            source_stats[source.name].update(
                {
                    "processed": processed,
                    "matches": relevant,
                    "errors": source_errors + len(getattr(source, "warnings", [])),
                }
            )

        if not args.dry_run:
            all_matches = database.all_matches()
            write_csv(all_matches)
            write_site_data(all_matches, ROOT / "site" / "data.json")
            report_path = REPORT_DIR / f"{date.today().isoformat()}.md"
            write_report(
                report_path,
                since=since,
                source_counts=source_counts,
                matches=matches,
                failures=failures,
                dry_run=False,
            )
            logger.info("Relatório: %s", report_path)
        if not args.dry_run and email_enabled:
            pending = database.pending_notifications()
            if pending:
                try:
                    send_notification([item for _, item in pending], config["email"])
                except Exception:
                    logger.exception("Falha ao enviar e-mail; a notificação será tentada novamente.")
                    raise
                database.mark_notifications_sent([key for key, _ in pending])
        elif matches and args.dry_run:
            logger.info("Dry-run: %d correspondência(s); nenhuma notificação enviada.", len(matches))
        if args.dry_run:
            print("Resumo da consulta (dry-run):")
            for name, stats in source_stats.items():
                print(
                    f"- {name}: encontrados={stats['fetched']}, "
                    f"processados={stats['processed']}, relevantes={stats['matches']}, "
                    f"alta={stats['relevance']['alta']}, "
                    f"média={stats['relevance']['média']}, "
                    f"baixa={stats['relevance']['baixa']}, erros={stats['errors']}"
                )
            print(f"- Total relevante: {len(matches)}")
        logger.info("Concluído: %d correspondência(s), %d erro(s).", len(matches), len(failures))
    finally:
        if database:
            database.close()
    return 1 if not completed_sources else 0


if __name__ == "__main__":
    raise SystemExit(run())
