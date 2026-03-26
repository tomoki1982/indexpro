from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .models import SearchCandidate
from .settings import AppSettings


SEARCH_TERMS = [
    "{manufacturer} 代理店",
    "{manufacturer} 販売店",
    "{manufacturer} 取扱店",
    "{manufacturer} authorized distributor",
]


def load_fixture_candidates(fixture_path: Path, manufacturer_name: str) -> list[SearchCandidate]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    candidates: list[SearchCandidate] = []
    for page in fixture.get(manufacturer_name, []):
        candidates.append(
            SearchCandidate(
                manufacturer_name=manufacturer_name,
                url=page["url"],
                title=page["title"],
                snippet=page.get("body", "")[:180],
            )
        )
    return candidates


def search_with_duckduckgo(
    manufacturer_name: str, settings: AppSettings
) -> list[SearchCandidate]:
    headers = {"User-Agent": settings.user_agent}
    candidates: list[SearchCandidate] = []
    seen_urls: set[str] = set()

    for term in SEARCH_TERMS:
        query = quote_plus(term.format(manufacturer=manufacturer_name))
        response = requests.get(
            f"https://html.duckduckgo.com/html/?q={query}",
            headers=headers,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for result in soup.select(".result"):
            link = result.select_one(".result__a")
            snippet = result.select_one(".result__snippet")
            if not link or not link.get("href"):
                continue
            url = normalize_result_url(link["href"])
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(
                SearchCandidate(
                    manufacturer_name=manufacturer_name,
                    url=url,
                    title=link.get_text(" ", strip=True),
                    snippet=snippet.get_text(" ", strip=True) if snippet else "",
                )
            )
            if len(candidates) >= settings.max_search_results:
                return candidates

    return candidates


def normalize_result_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if re.match(r"^https?://", url):
        return url
    return ""

