from __future__ import annotations

from datetime import date
from pathlib import Path


def write_report(
    path: Path,
    *,
    since: date,
    source_counts: dict[str, int],
    matches: list[dict],
    failures: list[str],
    dry_run: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Monitoramento de atos em saúde — {date.today().isoformat()}",
        "",
        f"Período consultado a partir de **{since.isoformat()}**.",
    ]
    if dry_run:
        lines.append("**Execução de teste:** os resultados não foram gravados nem notificados.")
    lines.extend(["", "## Fontes", ""])
    if source_counts:
        lines.extend(f"- {name}: {count} documento(s) novo(s) processado(s)." for name, count in source_counts.items())
    else:
        lines.append("- Nenhuma fonte concluiu a consulta.")

    lines.extend(["", "## Atos relevantes para Contagem e a gestão municipal", ""])
    if not matches:
        lines.append("Nenhuma correspondência encontrada.")
    for item in matches:
        lines.extend(
            [
                f"### {item['number']} — {item['date']}",
                "",
                f"- **Fonte:** {item['source']}",
                f"- **Órgão:** {item.get('agency', 'Não identificado')}",
                f"- **Ementa/título:** {item['title'] or 'Não informado'}",
                f"- **Tipo:** {item['type']}",
                f"- **Tema:** {', '.join(item.get('theme', [])) or 'Não identificado'}",
                f"- **Relevância para Contagem:** {item.get('relevance', 'Não classificada')}",
                f"- **Valor:** {item.get('value') or 'Não identificado'}",
                f"- **Prazo/vigência:** {item.get('deadline') or 'Não identificado'}",
                f"- **Trecho:** “{item['snippet']}”",
                f"- **Link:** {item['url']}",
                "",
            ]
        )

    lines.extend(["## Falhas", ""])
    if failures:
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("Nenhuma falha registrada.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
