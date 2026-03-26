from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import (
    IndexProDistributor,
    IndexProManufacturer,
    IndexProProduct,
    IndexProResult,
    RawPage,
)
from .settings import AppSettings


INDEXPRO_BASE = "https://www.indexpro.co.jp"
INDEXPRO_MOBILE_BASE = "https://m.indexpro.co.jp"


@dataclass(slots=True)
class IndexProTargets:
    manufacturer_name: str
    products_url: str
    distributor_list_url: str


def load_indexpro_fixture(fixture_path: Path, manufacturer_name: str) -> IndexProResult:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture = payload[manufacturer_name]

    manufacturer = IndexProManufacturer(
        manufacturer_name=manufacturer_name,
        display_name=fixture["manufacturer"]["display_name"],
        manufacturer_url=fixture["manufacturer"]["manufacturer_url"],
        products_url=fixture["manufacturer"]["products_url"],
        distributor_list_url=fixture["manufacturer"]["distributor_list_url"],
        summary=fixture["manufacturer"].get("summary", ""),
    )

    products = [
        IndexProProduct(
            manufacturer_name=manufacturer_name,
            product_name=item["product_name"],
            product_url=item["product_url"],
            summary=item.get("summary", ""),
            category=item.get("category", ""),
        )
        for item in fixture.get("products", [])
    ]

    distributors = [
        IndexProDistributor(
            manufacturer_name=manufacturer_name,
            distributor_name=item["distributor_name"],
            distributor_url=item["distributor_url"],
            location_url=item["location_url"],
            handling_makers_url=item["handling_makers_url"],
            region=item.get("region", "不明"),
            distributor_type=item.get("distributor_type", "代理店・取扱店"),
            listed_source_url=item.get("listed_source_url", fixture["manufacturer"]["distributor_list_url"]),
            evidence=item.get("evidence", ""),
            handling_manufacturers=item.get("handling_manufacturers", []),
        )
        for item in fixture.get("distributors", [])
    ]

    raw_pages = [
        RawPage(
            manufacturer_name=manufacturer_name,
            url=item["url"],
            title=item["title"],
            body=item["body"],
            domain=urlparse(item["url"]).netloc,
            fetched_at=datetime.now(),
        )
        for item in fixture.get("raw_pages", [])
    ]

    return IndexProResult(
        manufacturers=[manufacturer],
        products=products,
        distributors=distributors,
        raw_pages=raw_pages,
    )


def fetch_indexpro_live(manufacturer_name: str, settings: AppSettings) -> IndexProResult:
    session = requests.Session()
    session.headers.update({"User-Agent": settings.user_agent})

    targets = find_indexpro_targets(session, manufacturer_name, settings)
    products_html = get_html(session, targets.products_url, settings)
    distributors_html = get_html(session, targets.distributor_list_url, settings)

    products_page = build_raw_page(manufacturer_name, targets.products_url, products_html)
    distributors_page = build_raw_page(manufacturer_name, targets.distributor_list_url, distributors_html)

    manufacturer = IndexProManufacturer(
        manufacturer_name=manufacturer_name,
        display_name=extract_display_name_from_products(products_html, manufacturer_name),
        manufacturer_url=targets.products_url,
        products_url=targets.products_url,
        distributor_list_url=targets.distributor_list_url,
        summary=extract_page_summary(products_html),
    )

    products = parse_products(manufacturer_name, targets.products_url, products_html)
    distributors = parse_distributors(manufacturer_name, targets.distributor_list_url, distributors_html)

    raw_pages = [products_page, distributors_page]
    for distributor in distributors:
        if not distributor.handling_makers_url:
            continue
        try:
            handling_html = get_html(session, distributor.handling_makers_url, settings)
        except requests.RequestException:
            continue
        distributor.handling_manufacturers = parse_handling_manufacturers(handling_html)
        raw_pages.append(build_raw_page(manufacturer_name, distributor.handling_makers_url, handling_html))

    return IndexProResult(
        manufacturers=[manufacturer],
        products=products,
        distributors=distributors,
        raw_pages=raw_pages,
    )


def find_indexpro_targets(
    session: requests.Session, manufacturer_name: str, settings: AppSettings
) -> IndexProTargets:
    if settings.indexpro_products_url and settings.indexpro_distributor_url:
        return IndexProTargets(
            manufacturer_name=manufacturer_name,
            products_url=settings.indexpro_products_url,
            distributor_list_url=settings.indexpro_distributor_url,
        )

    product_url = search_first_url(
        session,
        queries=[
            f'site:indexpro.co.jp/SearchProduct/ "{manufacturer_name}" indexPro',
            f"site:indexpro.co.jp/SearchProduct/ {manufacturer_name} indexPro",
            f"site:indexpro.co.jp {manufacturer_name} 製品情報一覧 indexPro",
        ],
        settings=settings,
        required_substrings=["/SearchProduct/"],
    )
    distributor_url = search_first_url(
        session,
        queries=[
            f'site:m.indexpro.co.jp/distributor/list-distributor "{manufacturer_name}" indexPro',
            f"site:m.indexpro.co.jp/distributor/list-distributor {manufacturer_name} indexPro",
            f"site:indexpro.co.jp/distributor {manufacturer_name} 代理店 取扱店 indexPro",
        ],
        settings=settings,
        required_substrings=["/distributor/list-distributor", "/distributor/"],
    )

    if not product_url:
        raise ValueError(f"indexPro の製品情報ページが見つかりませんでした: {manufacturer_name}")
    if not distributor_url:
        raise ValueError(f"indexPro の代理店ページが見つかりませんでした: {manufacturer_name}")

    return IndexProTargets(
        manufacturer_name=manufacturer_name,
        products_url=normalize_indexpro_url(product_url),
        distributor_list_url=normalize_indexpro_url(distributor_url),
    )


def search_first_url(
    session: requests.Session,
    queries: list[str],
    settings: AppSettings,
    required_substrings: list[str],
) -> str:
    for query in queries:
        response = session.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select(".result__a"):
            href = anchor.get("href", "")
            if "indexpro.co.jp" not in href:
                continue
            if any(token in href for token in required_substrings):
                return href
    return ""


def normalize_indexpro_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(INDEXPRO_BASE, url)
    return url


def get_html(session: requests.Session, url: str, settings: AppSettings) -> str:
    response = session.get(url, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    return response.text


def build_raw_page(manufacturer_name: str, url: str, html: str) -> RawPage:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url
    body = soup.get_text("\n", strip=True)
    return RawPage(
        manufacturer_name=manufacturer_name,
        url=url,
        title=title,
        body=body,
        domain=urlparse(url).netloc,
        fetched_at=datetime.now(),
    )


def extract_display_name_from_products(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    match = re.search(r'「?\"?([^"\n]+?)\"?\s*の製品情報一覧', text)
    return match.group(1).strip() if match else fallback


def extract_page_summary(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for paragraph in soup.select("p"):
        text = paragraph.get_text(" ", strip=True)
        if len(text) > 40:
            return text
    return ""


def parse_products(manufacturer_name: str, base_url: str, html: str) -> list[IndexProProduct]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[IndexProProduct] = []
    seen: set[str] = set()

    for anchor in soup.select("a"):
        text = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        if not text or len(text) < 4:
            continue
        if text in {"Home", "会社案内", "広告掲載", "お問合せ", "サイトマップ"}:
            continue
        if any(token in text for token in ["コンタクト", "代理店", "メーカー検索", "取扱メーカー"]):
            continue
        if text in seen:
            continue
        absolute_url = urljoin(base_url, href) if href else base_url
        category = infer_product_category(text)
        summary = extract_neighbor_text(anchor)
        products.append(
            IndexProProduct(
                manufacturer_name=manufacturer_name,
                product_name=text,
                product_url=absolute_url,
                summary=summary,
                category=category,
            )
        )
        seen.add(text)
        if len(products) >= 20:
            break

    return products


def infer_product_category(text: str) -> str:
    if "/" in text:
        return text.split("/")[0].strip()
    if "UPS" in text or "電源" in text:
        return "電源装置"
    if "センサ" in text:
        return "センサ"
    if "リレー" in text:
        return "リレー"
    return "不明"


def extract_neighbor_text(anchor) -> str:
    parent = anchor.parent
    if parent:
        text = parent.get_text(" ", strip=True)
        if text and text != anchor.get_text(" ", strip=True):
            return text[:300]
    return ""


def parse_distributors(
    manufacturer_name: str, list_url: str, html: str
) -> list[IndexProDistributor]:
    soup = BeautifulSoup(html, "html.parser")
    distributors: list[IndexProDistributor] = []
    seen_names: set[str] = set()

    for anchor in soup.select("a"):
        href = anchor.get("href", "")
        name = anchor.get_text(" ", strip=True)
        if not href or not name:
            continue
        if "did=" not in href:
            continue
        if any(token in name for token in ["Home", "サイトマップ", "取扱メーカー", "変更"]):
            continue
        normalized_url = urljoin(list_url, href)
        did = extract_did(normalized_url)
        if not did or name in seen_names:
            continue
        seen_names.add(name)
        location_url = f"{INDEXPRO_BASE}/distributor/location?did={did}"
        handling_url = f"{INDEXPRO_MOBILE_BASE}/distributor/handlingmaker?did={did}"
        region = infer_region_from_context(anchor)
        evidence = extract_anchor_context(anchor)
        distributors.append(
            IndexProDistributor(
                manufacturer_name=manufacturer_name,
                distributor_name=name,
                distributor_url=normalized_url,
                location_url=location_url,
                handling_makers_url=handling_url,
                region=region,
                distributor_type="代理店・取扱店",
                listed_source_url=list_url,
                evidence=evidence,
                handling_manufacturers=[],
            )
        )
    return distributors


def extract_did(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    values = query.get("did")
    return values[0] if values else ""


def infer_region_from_context(anchor) -> str:
    context = extract_anchor_context(anchor)
    region_map = {
        "北海道": ["北海道"],
        "東北": ["青森", "岩手", "宮城", "秋田", "山形", "福島", "東北"],
        "関東": ["東京", "神奈川", "千葉", "埼玉", "茨城", "栃木", "群馬"],
        "中部": ["新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知"],
        "近畿": ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "三重"],
        "中国": ["鳥取", "島根", "岡山", "広島", "山口"],
        "四国": ["徳島", "香川", "愛媛", "高知"],
        "九州": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"],
    }
    for region, keywords in region_map.items():
        if any(keyword in context for keyword in keywords):
            return region
    return "不明"


def extract_anchor_context(anchor) -> str:
    parent = anchor.parent
    if not parent:
        return anchor.get_text(" ", strip=True)
    text = parent.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)[:300]


def parse_handling_manufacturers(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names: list[str] = []
    seen: set[str] = set()
    for item in soup.select("li, a"):
        text = item.get_text(" ", strip=True)
        if not text or len(text) <= 1:
            continue
        if text in {"0-Z", "あ行", "か行", "さ行", "た行", "な行", "は行", "ま行", "や行", "ら行", "わ行"}:
            continue
        if any(token in text for token in ["取扱メーカー", "取扱メーカー数", "Home", "サイトマップ"]):
            continue
        if text in seen:
            continue
        seen.add(text)
        names.append(text)
    return names[:200]
