from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from .models import RawPage
from .settings import AppSettings


INDEXPRO_BASE = "https://www.indexpro.co.jp"
MANUFACTURER_INDEX_URL = f"{INDEXPRO_BASE}/distributor/search-maker"
DISTRIBUTOR_INDEX_URL = f"{INDEXPRO_BASE}/distributor/search-distributor"
INITIALS = ["09-D", "E-I", "J-N", "O-S", "T-Z", *list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわ")]


@dataclass(slots=True)
class DirectoryManufacturer:
    name: str
    initial: str
    listing_url: str
    distributor_list_url: str
    mcid: str


@dataclass(slots=True)
class DirectoryDistributor:
    name: str
    initial: str
    did: str
    company_url: str
    location_url: str
    online_sales_url: str
    source_category: str
    handling_makers_url: str


@dataclass(slots=True)
class DistributorHandling:
    did: str
    distributor_name: str
    handling_manufacturer_name: str


@dataclass(slots=True)
class ManufacturerDistributorRelation:
    mcid: str
    manufacturer_name: str
    distributor_name: str
    did: str
    relation_category: str
    company_url: str
    location_url: str
    online_sales_url: str


@dataclass(slots=True)
class IndexProDirectoryResult:
    manufacturers: list[DirectoryManufacturer]
    distributors: list[DirectoryDistributor]
    handlings: list[DistributorHandling]
    relations: list[ManufacturerDistributorRelation]
    raw_pages: list[RawPage]


def load_directory_fixture(fixture_path: Path) -> IndexProDirectoryResult:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    manufacturers = [
        DirectoryManufacturer(
            name=item["name"],
            initial=item["initial"],
            listing_url=item["listing_url"],
            distributor_list_url=item["distributor_list_url"],
            mcid=item["mcid"],
        )
        for item in payload.get("manufacturers", [])
    ]
    distributors = [
        DirectoryDistributor(
            name=item["name"],
            initial=item["initial"],
            did=item["did"],
            company_url=item["company_url"],
            location_url=item.get("location_url", ""),
            online_sales_url=item.get("online_sales_url", ""),
            source_category=item.get("source_category", "代理店・取扱店"),
            handling_makers_url=item["handling_makers_url"],
        )
        for item in payload.get("distributors", [])
    ]
    handlings = [
        DistributorHandling(
            did=item["did"],
            distributor_name=item["distributor_name"],
            handling_manufacturer_name=item["handling_manufacturer_name"],
        )
        for item in payload.get("handlings", [])
    ]
    relations = [
        ManufacturerDistributorRelation(
            mcid=item["mcid"],
            manufacturer_name=item["manufacturer_name"],
            distributor_name=item["distributor_name"],
            did=item.get("did", ""),
            relation_category=item["relation_category"],
            company_url=item.get("company_url", ""),
            location_url=item.get("location_url", ""),
            online_sales_url=item.get("online_sales_url", ""),
        )
        for item in payload.get("relations", [])
    ]
    raw_pages = [
        RawPage(
            manufacturer_name=item.get("context", "indexPro directory"),
            url=item["url"],
            title=item["title"],
            body=item["body"],
            domain=urlparse(item["url"]).netloc,
            fetched_at=datetime.now(),
        )
        for item in payload.get("raw_pages", [])
    ]
    return IndexProDirectoryResult(
        manufacturers=manufacturers,
        distributors=distributors,
        handlings=handlings,
        relations=relations,
        raw_pages=raw_pages,
    )


def fetch_directory_live(settings: AppSettings) -> IndexProDirectoryResult:
    session = requests.Session()
    session.headers.update({"User-Agent": settings.user_agent})

    manufacturers: list[DirectoryManufacturer] = []
    distributors: list[DirectoryDistributor] = []
    handlings: list[DistributorHandling] = []
    relations: list[ManufacturerDistributorRelation] = []
    raw_pages: list[RawPage] = []

    seen_mcid: set[str] = set()
    seen_did: set[str] = set()

    print(f"[1/4] メーカー一覧の巡回を開始します。対象インデックス数: {len(INITIALS)}", flush=True)
    for index, initial in enumerate(INITIALS, start=1):
        maker_url = f"{MANUFACTURER_INDEX_URL}?initial={initial}"
        maker_html = get_html(session, maker_url, settings)
        before_count = len(manufacturers)
        for item in parse_manufacturer_listing(maker_url, maker_html, initial):
            if item.mcid in seen_mcid:
                continue
            seen_mcid.add(item.mcid)
            manufacturers.append(item)
        added_count = len(manufacturers) - before_count
        print(
            f"  メーカー索引 {index}/{len(INITIALS)} [{initial}] 完了: +{added_count}件 / 累計 {len(manufacturers)}件",
            flush=True,
        )
        sleep_if_needed(settings)

    print(f"[2/4] 代理店・取扱店一覧の巡回を開始します。対象インデックス数: {len(INITIALS)}", flush=True)
    for index, initial in enumerate(INITIALS, start=1):
        distributor_url = f"{DISTRIBUTOR_INDEX_URL}?initial={initial}"
        distributor_html = get_html(session, distributor_url, settings)
        before_count = len(distributors)
        for item in parse_distributor_listing(distributor_url, distributor_html, initial):
            if item.did in seen_did:
                continue
            seen_did.add(item.did)
            distributors.append(item)
        added_count = len(distributors) - before_count
        print(
            f"  代理店索引 {index}/{len(INITIALS)} [{initial}] 完了: +{added_count}件 / 累計 {len(distributors)}件",
            flush=True,
        )
        sleep_if_needed(settings)

    print(f"[3/4] 代理店ごとの取扱メーカー取得を開始します。対象代理店数: {len(distributors)}", flush=True)
    for index, distributor in enumerate(distributors, start=1):
        handling_html = get_html(session, distributor.handling_makers_url, settings)
        names = parse_handling_manufacturers(handling_html)
        for name in names:
            handlings.append(
                DistributorHandling(
                    did=distributor.did,
                    distributor_name=distributor.name,
                    handling_manufacturer_name=name,
                )
            )
        if index <= 10 or index % 100 == 0 or index == len(distributors):
            print(
                f"  取扱メーカー取得 {index}/{len(distributors)}: {distributor.name} -> {len(names)}件 / 累計関係数 {len(handlings)}件",
                flush=True,
            )
        sleep_if_needed(settings)

    print(f"[4/4] メーカー別の代理店・取扱店区分取得を開始します。対象メーカー数: {len(manufacturers)}", flush=True)
    for index, manufacturer in enumerate(manufacturers, start=1):
        relation_html = get_html(session, manufacturer.distributor_list_url, settings)
        page_relations = parse_manufacturer_distributor_relations(
            manufacturer.distributor_list_url,
            relation_html,
            manufacturer,
        )
        relations.extend(page_relations)
        if index <= 10 or index % 100 == 0 or index == len(manufacturers):
            print(
                f"  関係区分取得 {index}/{len(manufacturers)}: {manufacturer.name} -> {len(page_relations)}件 / 累計関係数 {len(relations)}件",
                flush=True,
            )
        sleep_if_needed(settings)

    print(
        f"完了: メーカー {len(manufacturers)}件 / 代理店・取扱店 {len(distributors)}件 / 取扱関係 {len(handlings)}件 / メーカー別関係 {len(relations)}件",
        flush=True,
    )

    return IndexProDirectoryResult(
        manufacturers=sorted(manufacturers, key=lambda x: x.name),
        distributors=sorted(distributors, key=lambda x: x.name),
        handlings=sorted(handlings, key=lambda x: (x.distributor_name, x.handling_manufacturer_name)),
        relations=sorted(relations, key=lambda x: (x.manufacturer_name, x.relation_category, x.distributor_name)),
        raw_pages=raw_pages,
    )


def get_html(session: requests.Session, url: str, settings: AppSettings) -> str:
    response = session.get(url, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    return response.text


def parse_manufacturer_listing(page_url: str, html: str, initial: str) -> list[DirectoryManufacturer]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[DirectoryManufacturer] = []
    seen_mcid: set[str] = set()
    for block in soup.select("div.search_list dl"):
        company_anchor = block.select_one("dt span.company a")
        list_anchor = block.select_one("a[href*='list-distributor?mcid=']")
        if not company_anchor or not list_anchor:
            continue
        mcid = extract_query_value(list_anchor.get("href", ""), "mcid")
        name = normalize_text(company_anchor.get_text(" ", strip=True))
        if not mcid or mcid in seen_mcid or not is_real_name(name):
            continue
        results.append(
            DirectoryManufacturer(
                name=name,
                initial=initial,
                listing_url=page_url,
                distributor_list_url=urljoin(page_url, list_anchor.get("href", "")),
                mcid=mcid,
            )
        )
        seen_mcid.add(mcid)
    return results


def parse_distributor_listing(page_url: str, html: str, initial: str) -> list[DirectoryDistributor]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[DirectoryDistributor] = []
    seen_did: set[str] = set()

    for block in soup.select("div.search_list dl"):
        company_anchor = block.select_one("dt span.company a[href*='/distributor/link/contact?d_web=']")
        location_anchor = block.select_one("dd.contactlink a[href*='/distributor/location?did=']")
        handling_anchor = block.select_one("dd.contactlink a[href*='/distributor/handlingmaker?did=']")
        online_sales_anchor = find_anchor_by_text(block, "オンライン販売")
        if not company_anchor or not location_anchor or not handling_anchor:
            continue

        did = extract_query_value(handling_anchor.get("href", ""), "did")
        name = normalize_text(company_anchor.get_text(" ", strip=True))
        if not did or did in seen_did or not is_real_name(name):
            continue

        online_sales_url = urljoin(page_url, online_sales_anchor.get("href", "")) if online_sales_anchor else ""
        results.append(
            DirectoryDistributor(
                name=name,
                initial=initial,
                did=did,
                company_url=urljoin(page_url, company_anchor.get("href", "")),
                location_url=urljoin(page_url, location_anchor.get("href", "")),
                online_sales_url=online_sales_url,
                source_category="オンライン販売" if online_sales_url else "代理店・取扱店",
                handling_makers_url=urljoin(page_url, handling_anchor.get("href", "")),
            )
        )
        seen_did.add(did)

    return results


def parse_handling_manufacturers(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("div.handlingmaker_list a[href^='/CompanyLink/']"):
        text = normalize_text(anchor.get_text(" ", strip=True))
        if not text or len(text) <= 1 or text in seen:
            continue
        seen.add(text)
        names.append(text)
    return names


def parse_manufacturer_distributor_relations(
    page_url: str,
    html: str,
    manufacturer: DirectoryManufacturer,
) -> list[ManufacturerDistributorRelation]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[ManufacturerDistributorRelation] = []
    seen: set[tuple[str, str, str]] = set()

    for company_anchor in soup.select("a[href*='/distributor/link/contact?d_web=']"):
        distributor_name = normalize_text(company_anchor.get_text(" ", strip=True))
        if not is_real_name(distributor_name):
            continue

        container = find_relation_container(company_anchor)
        block_text = normalize_text(container.get_text(" ", strip=True))
        location_anchor = find_anchor_by_text(container, "営業拠点")
        online_sales_anchor = find_anchor_by_text(container, "オンライン販売")

        did = ""
        if location_anchor is not None:
            did = extract_query_value(location_anchor.get("href", ""), "did")
        if not did and online_sales_anchor is not None:
            did = extract_query_value(online_sales_anchor.get("href", ""), "did")

        relation_category = infer_relation_category(block_text)
        key = (manufacturer.mcid, did, distributor_name)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            ManufacturerDistributorRelation(
                mcid=manufacturer.mcid,
                manufacturer_name=manufacturer.name,
                distributor_name=distributor_name,
                did=did,
                relation_category=relation_category,
                company_url=urljoin(page_url, company_anchor.get("href", "")),
                location_url=urljoin(page_url, location_anchor.get("href", "")) if location_anchor else "",
                online_sales_url=urljoin(page_url, online_sales_anchor.get("href", "")) if online_sales_anchor else "",
            )
        )

    return results


def find_relation_container(anchor: Tag) -> Tag:
    current: Tag | None = anchor
    while current is not None:
        if current.name in {"dl", "li", "div"}:
            return current
        parent = current.parent
        current = parent if isinstance(parent, Tag) else None
    return anchor


def infer_relation_category(text: str) -> str:
    normalized = normalize_text(text)
    if "正規代理店" in normalized or "代理店" in normalized:
        return "代理店"
    if "取扱店" in normalized:
        return "取扱店"
    if "オンライン" in normalized:
        return "オンライン販売"
    return "未設定"


def find_anchor_by_text(block: Tag, text: str) -> Tag | None:
    for anchor in block.select("a[href]"):
        label = normalize_text(anchor.get_text(" ", strip=True))
        if text in label:
            return anchor
    return None


def extract_query_value(href: str, name: str) -> str:
    query = parse_qs(urlparse(urljoin(INDEXPRO_BASE, href)).query)
    values = query.get(name)
    return values[0] if values else ""


def is_real_name(text: str) -> bool:
    if not text:
        return False
    if text in {"代理店・取扱店", "営業拠点", "取扱メーカー", "オンライン販売"}:
        return False
    return True


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sleep_if_needed(settings: AppSettings) -> None:
    if getattr(settings, "crawl_delay_seconds", 0) > 0:
        time.sleep(settings.crawl_delay_seconds)
