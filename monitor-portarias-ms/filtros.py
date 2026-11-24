from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fontes.base import Document


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def find_contagem_match(text: str, settings: dict | None = None) -> dict | None:
    settings = settings or {}
    normalized = normalize(text)
    codes = settings.get("ibge_codes", ["3118601", "311860"])
    institutions = [
        normalize(term)
        for term in settings.get(
            "institutional_terms",
            [
                "Município de Contagem",
                "Prefeitura Municipal de Contagem",
                "Fundo Municipal de Saúde de Contagem",
                "SMS Contagem",
            ],
        )
    ]
    state_terms = [
        normalize(term) for term in settings.get("state_terms", ["MG", "Minas Gerais"])
    ]

    for term in institutions:
        if term in normalized:
            return _snippet(text, term)

    for code in codes:
        if re.search(rf"(?<!\d){re.escape(str(code))}(?!\d)", normalized):
            return _snippet(text, str(code))

    for clause in re.split(r"[\n.!?;]+", normalized):
        if not re.search(r"\bcontagem\b", clause):
            continue
        if re.search(r"\bcontagem\s+(?:de\s+)?(?:casos|regressiva)\b", clause):
            continue
        state_pattern = r"\b(?:" + "|".join(re.escape(term) for term in state_terms) + r")\b"
        if state_terms and re.search(state_pattern, clause):
            original_clause = next(
                (part for part in re.split(r"[\n.!?;]+", text) if normalize(part).strip() == clause.strip()),
                clause,
            )
            return _snippet(original_clause, "contagem")
    return None


def _snippet(text: str, term: str, limit: int = 360) -> dict:
    normalized = normalize(text)
    position = normalized.find(normalize(term))
    if position < 0:
        position = 0
    start = max(0, position - limit // 3)
    end = min(len(text), start + limit)
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    if start:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt += "..."
    return {"snippet": excerpt}


def infer_type(text: str, title: str = "") -> str:
    normalized = normalize(f"{title} {text}")
    categories = (
        ("habilitação", r"\bhabilit"),
        ("credenciamento", r"\bcredenci"),
        ("incentivo", r"\bincentiv"),
        ("recurso", r"\brecursos?\b|\bfinanceir"),
        ("transferência", r"\btransfer"),
        ("instituição de programa", r"\binstitui"),
    )
    for label, pattern in categories:
        if re.search(pattern, normalized):
            return label
    return "Portaria"


def classify_type(text: str, title: str = "") -> str:
    normalized = normalize(f"{title} {text}")
    categories = (
        ("habilitação", r"\bhabilit"),
        ("incentivo", r"\bincentiv"),
        ("repasse", r"\brepass|\btransfer[eê]ncia de recursos|\btransferir recursos"),
        ("pactuação", r"\bpactua|\bcib(?:-sus)?\b"),
        ("regulamentação", r"\b(?:rdc|resolu[cç][aã]o|portaria|instru[cç][aã]o normativa)\b"),
    )
    for label, pattern in categories:
        if re.search(pattern, normalized):
            return label
    return "outros"


def classify_theme(text: str, theme_settings: dict | None = None) -> list[str]:
    normalized = normalize(text)
    themes = theme_settings or {}
    return [
        label
        for label, terms in themes.items()
        if any(normalize(term) in normalized for term in terms)
    ]


def classify_relevance(
    text: str,
    settings: dict | None = None,
    *,
    direct_match: bool | None = None,
) -> str:
    settings = settings or {}
    if direct_match is None:
        direct_match = find_contagem_match(text, settings) is not None
    if direct_match:
        return "alta"
    normalized = normalize(text)
    scope_terms = settings.get("municipal_scope_terms", [])
    region_terms = settings.get("bh_region_terms", [])
    if any(normalize(term) in normalized for term in [*scope_terms, *region_terms]):
        return "média"
    return "baixa"


def classify_document(
    document: Document,
    text: str,
    source_key: str,
    config: dict,
) -> dict | None:
    filters = config.get("filters", {})
    searchable = "\n".join((document.title, document.summary, text))
    contagem_match = find_contagem_match(searchable, filters)
    relevance = classify_relevance(searchable, filters, direct_match=contagem_match is not None)
    themes = classify_theme(searchable, config.get("themes", {}))

    if source_key == "anvisa":
        if not themes:
            return None
    elif relevance == "baixa":
        return None

    snippet = contagem_match or _snippet(searchable, _relevance_term(searchable, filters))
    if not contagem_match and document.summary:
        snippet = {"snippet": _snippet(document.summary, "", 360)["snippet"]}
    return {
        "source": document.source or _source_name(source_key),
        "agency": document.agency or _agency(source_key),
        "number": document.number or extract_number(document.title, text) or "Não identificado",
        "date": document.published or "Não identificada",
        "title": document.title,
        "ementa": document.summary or document.title,
        "type": classify_type(text, document.title),
        "theme": themes,
        "relevance": relevance,
        "municipal_mentions": _municipal_mentions(searchable),
        "value": extract_value(text),
        "deadline": extract_deadline(text),
        "snippet": snippet["snippet"],
        "url": document.url,
    }


def _agency(source_key: str) -> str:
    return {
        "dou": "Ministério da Saúde",
        "bvs": "Ministério da Saúde",
        "govbr": "Ministério da Saúde",
        "sesmg": "Secretaria de Estado de Saúde de Minas Gerais",
        "iofmg": "Governo de Minas Gerais",
        "anvisa": "Agência Nacional de Vigilância Sanitária",
    }.get(source_key, source_key)


def _source_name(source_key: str) -> str:
    return {
        "dou": "Diário Oficial da União — Seção 1",
        "bvs": "Saúde Legis / BVS",
        "govbr": "Ministério da Saúde — gov.br",
        "sesmg": "Secretaria de Estado de Saúde de Minas Gerais",
        "iofmg": "Diário Oficial de Minas Gerais — Executivo",
        "anvisa": "AnvisaLegis",
    }.get(source_key, source_key)


def _relevance_term(text: str, filters: dict) -> str:
    normalized = normalize(text)
    for term in [*filters.get("municipal_scope_terms", []), *filters.get("bh_region_terms", [])]:
        if normalize(term) in normalized:
            return term
    return ""


def _municipal_mentions(text: str) -> list[str]:
    normalized = normalize(text)
    mentions = []
    if re.search(r"\b(?:municipios|municipio)\b", normalized):
        mentions.append("municípios")
    if re.search(r"\bsecretarias municipais\b|\bsecretaria municipal\b", normalized):
        mentions.append("secretarias municipais")
    if re.search(r"\bcontagem\b|3118601|311860", normalized):
        mentions.append("Contagem")
    return mentions


def extract_value(text: str) -> str:
    match = re.search(
        r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})|R\$\s?\d+(?:,\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def extract_deadline(text: str) -> str:
    date_pattern = (
        r"(?:(?:prazo|vig[eê]ncia|validade|at[eé]|limite|encerramento)"
        r"[^\n.;]{0,80}?)\b(\d{2})/(\d{2})/(\d{4})\b"
    )
    match = re.search(date_pattern, text, flags=re.IGNORECASE)
    if match:
        day, month, year = match.groups()
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            return ""
    iso_pattern = (
        r"(?:(?:prazo|vig[eê]ncia|validade|at[eé]|limite|encerramento)"
        r"[^\n.;]{0,80}?)\b(\d{4})-(\d{2})-(\d{2})\b"
    )
    match = re.search(iso_pattern, text, flags=re.IGNORECASE)
    if match:
        year, month, day = match.groups()
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            return ""
    duration = re.search(
        r"\b(?:prazo|vig[eê]ncia|validade)\s+(?:de\s+)?(\d+\s+"
        r"(?:dias?|meses?|anos?))\b",
        text,
        flags=re.IGNORECASE,
    )
    if duration:
        return duration.group(1)
    return ""


def extract_number(title: str, text: str) -> str:
    pattern = (
        r"\b(?:portaria|resolucao|decreto)\b.{0,60}?"
        r"(?:n[º°o.]?\s*)?(\d[\d./-]*)"
    )
    for candidate in (title, text):
        match = re.search(pattern, candidate, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).rstrip(".,")
    return ""
