from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from fontes.base import BaseSource, Document, clean_html


class GovBR(BaseSource):
    key = "govbr"
    name = "Ministério da Saúde — gov.br"
    base_url = "https://www.gov.br/saude/pt-br"

    def fetch_documents(self, since: date) -> list[Document]:
        results: dict[str, Document] = {}
        for offset in range(0, 500, 100):
            query = urlencode(
                {
                    "SearchableText": "portaria",
                    "sort_on": "created",
                    "sort_order": "reverse",
                    "b_start": offset,
                    "b_size": 100,
                }
            )
            response = self.request(f"{self.base_url}/@@search?{query}")
            soup = BeautifulSoup(response.content, "html.parser")
            page_items = 0
            for anchor in soup.select("a[href]"):
                url = urljoin(self.base_url, anchor["href"].split("?")[0])
                if not url.startswith(self.base_url + "/") or "@@search" in url:
                    continue
                title = clean_html(anchor.get_text(" ", strip=True))
                if len(title) < 8:
                    continue
                parent = anchor.parent
                context = parent.get_text(" ", strip=True) if parent else title
                published = self._date(context)
                if published and published < since.isoformat():
                    continue
                if url not in results:
                    results[url] = Document(
                        title=title,
                        url=url,
                        number="",
                        published=published,
                        summary=context[:500],
                    )
                    page_items += 1
            if page_items == 0:
                break
        return list(results.values())

    @staticmethod
    def _date(text: str) -> str:
        match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
        if not match:
            return ""
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
