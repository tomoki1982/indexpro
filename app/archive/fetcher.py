from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .models import RawPage, SearchCandidate
from .settings import AppSettings


def load_fixture_pages(fixture_path, manufacturer_name: str) -> list[RawPage]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    pages: list[RawPage] = []
    for page in fixture.get(manufacturer_name, []):
        pages.append(
            RawPage(
                manufacturer_name=manufacturer_name,
                url=page["url"],
                title=page["title"],
                body=page["body"],
                domain=urlparse(page["url"]).netloc,
                fetched_at=datetime.now(),
            )
        )
    return pages


def fetch_pages(
    candidates: list[SearchCandidate], settings: AppSettings
) -> list[RawPage]:
    headers = {"User-Agent": settings.user_agent}
    pages: list[RawPage] = []

    for candidate in candidates:
        try:
            response = requests.get(
                candidate.url,
                headers=headers,
                timeout=settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        title = extract_title(soup, fallback=candidate.title)
        body = extract_text(soup)
        if len(body) < 80:
            continue
        pages.append(
            RawPage(
                manufacturer_name=candidate.manufacturer_name,
                url=candidate.url,
                title=title,
                body=body,
                domain=urlparse(candidate.url).netloc,
                fetched_at=datetime.now(),
            )
        )
    return pages


def extract_title(soup: BeautifulSoup, fallback: str = "") -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    return fallback


def extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

