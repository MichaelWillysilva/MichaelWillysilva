from __future__ import annotations

import base64
import io
import re
from datetime import date, timedelta

import requests
from pypdf import PdfReader

from filtros import find_contagem_match
from fontes.base import BaseSource, Document


class IOFMG(BaseSource):
    key = "iofmg"
    name = "Diário Oficial de Minas Gerais — Executivo"
    base_url = "https://www.jornalminasgerais.mg.gov.br"
    api_url = f"{base_url}/api/v1/Jornal/ObterEdicaoPorDataPublicacao"

    def fetch_documents(self, since: date) -> list[Document]:
        documents = []
        issue_date = since
        while issue_date <= date.today():
            response = self.request(
                self.api_url,
                params={"dataPublicacao": issue_date.isoformat()},
            )
            payload = response.json()
            issue = payload.get("dados") if isinstance(payload, dict) else None
            if issue:
                documents.extend(self._documents_from_issue(issue, issue_date))
            issue_date += timedelta(days=1)
        return documents

    def _documents_from_issue(self, issue: dict, issue_date: date) -> list[Document]:
        archive = issue.get("arquivoCadernoPrincipal") or {}
        encoded = archive.get("arquivo", "")
        if not encoded:
            return []
        binary = base64.b64decode(encoded)
        pdf_start = binary.find(b"%PDF")
        if pdf_start < 0:
            raise ValueError(f"PDF do Diário Oficial de {issue_date} não encontrado na resposta.")
        reader = PdfReader(io.BytesIO(binary[pdf_start:]))
        results = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not self._is_relevant_page(text):
                continue
            heading = next((line.strip() for line in text.splitlines() if line.strip()), "")
            title = f"{heading[:180] or 'Diário do Executivo'} — pág. {page_number}"
            url = f"{self.base_url}/edicao-do-dia"
            results.append(
                Document(
                    title=title,
                    url=url,
                    published=issue_date.isoformat(),
                    summary=heading or title,
                    source=self.name,
                    agency="Governo de Minas Gerais / SES-MG",
                    content=text,
                )
            )
        return results

    def _is_relevant_page(self, text: str) -> bool:
        normalized = text.casefold()
        if find_contagem_match(text, self.config.get("filters", {})):
            return True
        scope_terms = self.config.get("filters", {}).get("municipal_scope_terms", [])
        if any(term.casefold() in normalized for term in scope_terms):
            return True
        health_term = re.search(
            r"secretaria.{0,30}estado.{0,20}sa[uú]de|cib[- ]sus|"
            r"secretaria.{0,20}sa[uú]de",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        act_term = re.search(
            r"\b(portaria|resolu[cç][aã]o|delibera[cç][aã]o|habilita[cç][aã]o|"
            r"repasse|incentivo|pactua[cç][aã]o)\b",
            text,
            flags=re.IGNORECASE,
        )
        return bool(health_term and act_term)
