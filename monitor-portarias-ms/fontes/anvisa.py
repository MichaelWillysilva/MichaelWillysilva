from __future__ import annotations

import math
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fontes.base import BaseSource, Document, clean_html


class Anvisa(BaseSource):
    key = "anvisa"
    name = "AnvisaLegis"
    base_url = "https://anvisalegis.datalegis.net"
    search_url = f"{base_url}/action/ActionDatalegis.php"
    form_url = (
        f"{search_url}?acao=abrirLegislacao&cod_modulo=310&cod_menu=9434"
    )
    page_size = 100

    def fetch_documents(self, since: date) -> list[Document]:
        response = self.request(self.form_url)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find("form", id="formPesquisaPrincipal")
        if form is None:
            raise ValueError("Formulário de pesquisa pública do AnvisaLegis não encontrado.")

        payload = self._form_payload(form)
        payload.update(
            {
                "dta_promulgacao": since.strftime("%d/%m/%Y"),
                "dta_promulgacao_final": date.today().strftime("%d/%m/%Y"),
                "in_pesquisa_avancada": "S",
                "qtd_pagina": str(self.page_size),
            }
        )
        action = urljoin(self.base_url, form.get("action") or self.search_url)
        result_page = self.request(action, method="POST", data=payload)
        soup = BeautifulSoup(result_page.content, "html.parser")
        result_form = soup.find("form", id="formPesquisaPrincipal")
        if result_form is None:
            raise ValueError("O AnvisaLegis não retornou o formulário de resultados.")

        result_payload = self._form_payload(result_form)
        result_payload["qtd_pagina"] = str(self.page_size)
        documents: dict[str, Document] = {}
        total_items = self._result_count(soup)
        pages = max(1, math.ceil(total_items / self.page_size))
        for page_number in range(1, pages + 1):
            result_payload["pagina"] = str(page_number)
            page = self.request(
                self.search_url,
                method="POST",
                params={
                    "acao": "abrirPagina",
                    "pagina": page_number,
                    "legisjuris": "L",
                },
                data=result_payload,
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            try:
                result_json = page.json()
            except ValueError as exc:
                raise ValueError("Resposta inesperada ao carregar atos do AnvisaLegis.") from exc
            html = result_json.get("resultado", "")
            for anchor in BeautifulSoup(html, "html.parser").select("a[href]"):
                title = clean_html(anchor.get_text(" ", strip=True))
                url = urljoin(self.base_url, anchor["href"])
                if not title or "abrirTextoAto" not in url:
                    continue
                summary_node = anchor.find("p")
                summary = clean_html(summary_node.get_text(" ", strip=True)) if summary_node else title
                documents[url] = Document(
                    title=title,
                    url=url,
                    number=self._number(title),
                    published=self._date(title),
                    summary=summary,
                    source=self.name,
                    agency="Agência Nacional de Vigilância Sanitária",
                )
        return list(documents.values())

    @staticmethod
    def _form_payload(form) -> dict:
        data: dict[str, str | list[str]] = {}
        for element in form.select("input[name]"):
            if element.get("type") in {"submit", "button", "checkbox", "radio"}:
                continue
            data[element["name"]] = element.get("value", "")
        for select in form.select("select[name]"):
            selected = [option.get("value", "") for option in select.select("option[selected]")]
            if selected:
                data[select["name"]] = selected
        return data

    @staticmethod
    def _result_count(soup: BeautifulSoup) -> int:
        text = soup.get_text(" ", strip=True)
        match = re.search(r"Resultado da Busca:\s*([\d.]+)", text, flags=re.IGNORECASE)
        if not match:
            return 0
        return int(match.group(1).replace(".", ""))

    @staticmethod
    def _number(title: str) -> str:
        match = re.search(r"\bn[º°o.]?\s*([\d.]+)", title, flags=re.IGNORECASE)
        return match.group(1).replace(".", "") if match else ""

    @staticmethod
    def _date(title: str) -> str:
        match = re.search(r"\bde\s+(\d{2})/(\d{2})/(\d{4})", title, flags=re.IGNORECASE)
        if not match:
            return ""
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
