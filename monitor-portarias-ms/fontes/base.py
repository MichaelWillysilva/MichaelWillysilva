from __future__ import annotations

import io
import logging
import re
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


@dataclass
class Document:
    title: str
    url: str
    number: str = ""
    published: str = ""
    summary: str = ""
    source: str = ""
    agency: str = ""
    content: str = ""


class BaseSource:
    key = ""
    name = ""
    base_url = ""

    def __init__(self, config: dict):
        self.config = config
        self.settings = config.get("http", {})
        self.user_agent = self.settings.get(
            "user_agent", "MonitorPortariasContagem/1.0 (contato: admin@example.org)"
        )
        self.delay = float(self.settings.get("delay_seconds", 2))
        self.retries = int(self.settings.get("retries", 3))
        self.timeout = int(self.settings.get("timeout_seconds", 30))
        self._last_request = 0.0
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self.logger = logging.getLogger(f"fontes.{self.key}")

    def fetch_documents(self, since: date) -> list[Document]:
        raise NotImplementedError

    def fetch_full_text(self, document: Document) -> str:
        if document.content:
            return document.content
        response = self.request(document.url)
        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" in content_type or response.content.startswith(b"%PDF"):
            reader = PdfReader(io.BytesIO(response.content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        soup = BeautifulSoup(response.content, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()
        return soup.get_text("\n", strip=True)

    def request(self, url: str, *, method: str = "GET", **kwargs) -> requests.Response:
        origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if origin not in self._robots:
            robots_url = f"{origin}/robots.txt"
            response = self._request_with_retry(robots_url, check_robots=False)
            if response.status_code == 404:
                parser = urllib.robotparser.RobotFileParser()
                parser.parse([])
            elif response.status_code >= 400:
                raise requests.HTTPError(
                    f"Não foi possível verificar robots.txt ({response.status_code})",
                    response=response,
                )
            else:
                parser = urllib.robotparser.RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(response.text.splitlines())
            self._robots[origin] = parser
        if not self._robots[origin].can_fetch(self.user_agent, url):
            raise PermissionError(f"Acesso bloqueado por robots.txt: {url}")
        return self._request_with_retry(url, method=method, **kwargs)

    def _request_with_retry(
        self, url: str, *, check_robots: bool = True, method: str = "GET", **kwargs
    ) -> requests.Response:
        for attempt in range(self.retries + 1):
            elapsed = time.monotonic() - self._last_request
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                self._last_request = time.monotonic()
                if response.status_code == 404 and not check_robots:
                    return response
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except (requests.RequestException, OSError) as exc:
                status = (
                    exc.response.status_code
                    if isinstance(exc, requests.RequestException) and exc.response is not None
                    else None
                )
                if attempt >= self.retries or (
                    status is not None and status != 429 and status < 500
                ):
                    raise
                wait = min(2**attempt, 30)
                self.logger.warning("Falha na requisição %s; nova tentativa em %ss", url, wait)
                time.sleep(wait)
        raise RuntimeError(f"Falha ao requisitar {url}")


def clean_html(value: str) -> str:
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def date_text(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        return match.group(0) if match else value[:10]
