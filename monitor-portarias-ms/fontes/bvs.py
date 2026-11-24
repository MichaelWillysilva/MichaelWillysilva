from __future__ import annotations

from datetime import date, datetime, time
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from fontes.base import BaseSource, Document, clean_html


class BVS(BaseSource):
    key = "bvs"
    name = "Saúde Legis / BVS"
    base_url = "https://bvsms.saude.gov.br"
    legis_url = "https://saudelegis.saude.gov.br/saudelegis/secure/norma/listPublic.xhtml"

    def fetch_documents(self, since: date) -> list[Document]:
        self.warnings: list[str] = []
        try:
            documents = self._fetch_saudelegis(since)
            if documents:
                return documents
            self.logger.info("Saúde Legis não retornou normas; consultando o índice BVS.")
        except Exception as exc:
            warning = f"Saúde Legis indisponível; usado fallback da API BVS: {exc}"
            self.warnings.append(warning)
            self.logger.warning(warning)
        return self._fetch_bvs_posts(since)

    def _fetch_saudelegis(self, since: date) -> list[Document]:
        page = self.request(self.legis_url)
        soup = BeautifulSoup(page.content, "html.parser")
        form = soup.find("form", id="form")
        if form is None:
            raise ValueError("Formulário público de consulta Saúde Legis não encontrado.")

        data = {
            element["name"]: element.get("value", "")
            for element in form.select("input[name]")
        }
        for select in form.select("select[name]"):
            selected = select.select_one("option[selected]")
            data[select["name"]] = selected.get("value", "") if selected else ""
        data.update(
            {
                "form:data": since.strftime("%d/%m/%Y"),
                "form:dataAte": date.today().strftime("%d/%m/%Y"),
                "form:fonte": "105",
                "form:secao": "70",
            }
        )
        submit = form.select_one('input[type="submit"][value="Consultar"]')
        if submit and submit.get("name"):
            data[submit["name"]] = submit.get("value", "Consultar")
        action = urljoin(self.legis_url, form.get("action") or self.legis_url)
        response = self.request(action, method="POST", data=data)
        results = BeautifulSoup(response.content, "html.parser")
        documents = {}
        for row in results.select("table tr"):
            row_text = clean_html(row.get_text(" ", strip=True))
            published = self._date(row_text)
            for anchor in row.select("a[href]"):
                url = urljoin(self.legis_url, anchor["href"])
                if url.startswith("#") or "javascript:" in url:
                    continue
                title = clean_html(anchor.get_text(" ", strip=True)) or row_text
                if len(title) < 4:
                    continue
                documents[url] = Document(
                    title=title,
                    url=url,
                    number=self._number(title),
                    published=published,
                    summary=row_text,
                )
        return list(documents.values())

    def _fetch_bvs_posts(self, since: date) -> list[Document]:
        found: dict[str, Document] = {}
        after = datetime.combine(since, time.min).isoformat()
        for page in range(1, 11):
            response = self.request(
                f"{self.base_url}/wp-json/wp/v2/posts",
                params={
                    "search": "portaria",
                    "after": after,
                    "per_page": 100,
                    "page": page,
                    "_fields": "date,link,title,content,excerpt",
                },
            )
            items = response.json()
            if not isinstance(items, list):
                raise ValueError("Resposta inesperada da API REST da BVS.")
            if not items:
                break
            for item in items:
                title = clean_html(item.get("title", {}).get("rendered", ""))
                content = clean_html(item.get("content", {}).get("rendered", ""))
                summary = clean_html(item.get("excerpt", {}).get("rendered", "")) or content[:500]
                found[item["link"]] = Document(
                    title=title,
                    url=item["link"],
                    number="",
                    published=item.get("date", "")[:10],
                    summary=summary,
                )
            if len(items) < 100:
                break
        return list(found.values())

    @staticmethod
    def _date(text: str) -> str:
        match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
        if not match:
            return ""
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    @staticmethod
    def _number(title: str) -> str:
        match = re.search(r"\b(?:n[º°o.]?\s*)?(\d[\d./-]*)\b", title, re.IGNORECASE)
        return match.group(1) if match else ""
