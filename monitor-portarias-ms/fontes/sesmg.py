from __future__ import annotations

from datetime import date, datetime, time

from fontes.base import BaseSource, Document, clean_html


class SESMG(BaseSource):
    key = "sesmg"
    name = "Secretaria de Estado de Saúde de Minas Gerais"
    base_url = "https://www.saude.mg.gov.br"
    search_url = f"{base_url}/wp-json/wp/v2/posts"

    def fetch_documents(self, since: date) -> list[Document]:
        after = datetime.combine(since, time.min).isoformat()
        search_terms = self.config.get("sources", {}).get(
            "sesmg_search_terms",
            ["deliberação CIB-SUS", "CIB-SUS", "resolução SES", "habilitação SUS"],
        )
        found: dict[str, Document] = {}
        for term in search_terms:
            page_number = 1
            while True:
                response = self.request(
                    self.search_url,
                    params={
                        "search": term,
                        "after": after,
                        "per_page": 100,
                        "page": page_number,
                        "_fields": "date,link,title,content,excerpt",
                    },
                )
                items = response.json()
                if not isinstance(items, list):
                    raise ValueError("Resposta inesperada da API REST da SES-MG.")
                for item in items:
                    rendered = item.get("content", {}).get("rendered", "")
                    title = clean_html(item.get("title", {}).get("rendered", ""))
                    full_text = clean_html(rendered)
                    summary = clean_html(item.get("excerpt", {}).get("rendered", "")) or title
                    found[item["link"]] = Document(
                        title=title,
                        url=item["link"],
                        published=item.get("date", "")[:10],
                        summary=summary,
                        source=self.name,
                        agency=self.name,
                        content=full_text,
                    )
                if len(items) < 100:
                    break
                page_number += 1
        return list(found.values())
