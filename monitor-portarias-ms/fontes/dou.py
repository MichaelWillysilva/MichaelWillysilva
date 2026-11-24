from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fontes.base import BaseSource, Document, clean_html


class DOU(BaseSource):
    key = "dou"
    name = "Diário Oficial da União — Seção 1"
    base_url = "https://www.in.gov.br"
    search_url = f"{base_url}/consulta/-/buscar/dou"

    def fetch_documents(self, since: date) -> list[Document]:
        today = date.today()
        params = {
            "q": "Ministério da Saúde",
            "s": "do1",
            "exactDate": "personalizado",
            "from": since.strftime("%d-%m-%Y"),
            "to": today.strftime("%d-%m-%Y"),
            "sortType": "0",
        }
        response = self.request(self.search_url, params=params)
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" in content_type:
            return self._from_json(response.json())
        soup = BeautifulSoup(response.content, "html.parser")
        results = []
        seen = set()
        for anchor in soup.select('a[href*="/web/dou/-/"]'):
            url = urljoin(self.base_url, anchor.get("href", ""))
            if url in seen:
                continue
            seen.add(url)
            title = clean_html(anchor.get_text(" ", strip=True))
            if not title:
                continue
            results.append(
                Document(
                    title=title,
                    url=url,
                    number=self._number(title),
                    published=self._date(anchor),
                    summary=title,
                )
            )
        return results

    def _from_json(self, payload) -> list[Document]:
        results = []

        def visit(value):
            if isinstance(value, dict):
                title = value.get("title") or value.get("titulo") or value.get("ementa")
                url = value.get("url") or value.get("href") or value.get("urlDocumento")
                if isinstance(title, str) and isinstance(url, str):
                    results.append(
                        Document(
                            title=clean_html(title),
                            url=urljoin(self.base_url, url),
                            number=self._number(title),
                            published=str(value.get("date") or value.get("data") or "")[:10],
                            summary=clean_html(str(value.get("summary") or value.get("ementa") or title)),
                        )
                    )
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(payload)
        unique = {item.url: item for item in results}
        return list(unique.values())

    @staticmethod
    def _number(title: str) -> str:
        match = re.search(r"\b(?:n[ºo.]?\s*)?(\d[\d./-]*)\b", title, re.IGNORECASE)
        return match.group(1) if match else ""

    @staticmethod
    def _date(anchor) -> str:
        parent = anchor.parent
        for _ in range(4):
            if parent is None:
                break
            text = parent.get_text(" ", strip=True)
            match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", text)
            if match:
                day, month, year = match.group(0).split("/")
                return f"{year}-{month}-{day}"
            parent = parent.parent
        return ""
