from __future__ import annotations

import re
from collections import defaultdict

from .models import ExtractedCompany, RawPage


COMPANY_PATTERN = re.compile(
    r"([一-龠ぁ-んァ-ヴA-Za-z0-9・\-\(\)]+(?:株式会社|有限会社|合同会社|Inc\.|Co\., Ltd\.|Corporation|Company))"
)
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？.!?])\s+|\n+")

REGION_RULES = {
    "北海道": ["北海道"],
    "東北": ["青森", "岩手", "宮城", "秋田", "山形", "福島", "東北"],
    "関東": ["東京", "神奈川", "千葉", "埼玉", "茨城", "栃木", "群馬", "関東"],
    "中部": ["新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "中部"],
    "近畿": ["大阪", "京都", "兵庫", "奈良", "滋賀", "和歌山", "三重", "関西", "近畿"],
    "中国": ["鳥取", "島根", "岡山", "広島", "山口", "中国地方"],
    "四国": ["徳島", "香川", "愛媛", "高知", "四国"],
    "九州": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "九州"],
    "海外": ["overseas", "global", "海外", "asia", "europe", "usa"],
    "全国": ["全国", "all japan"],
}


def extract_companies(raw_pages: list[RawPage]) -> list[ExtractedCompany]:
    extracted: list[ExtractedCompany] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for page in raw_pages:
        sentences = split_sentences(page.body)
        for sentence in sentences:
            companies = COMPANY_PATTERN.findall(sentence)
            if not companies:
                continue
            for company_name in companies:
                if company_name == page.manufacturer_name:
                    continue
                category, category_score, category_notes = classify_category(sentence, page)
                stage, stage_score, stage_notes = estimate_stage(sentence, page, category)
                region = classify_region(sentence, page.body)
                score = round(min(0.99, 0.35 + category_score + stage_score), 2)
                notes = category_notes + stage_notes
                key = (page.manufacturer_name, company_name, sentence)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                extracted.append(
                    ExtractedCompany(
                        manufacturer_name=page.manufacturer_name,
                        company_name=normalize_company_name(company_name),
                        company_category=category,
                        region=region,
                        estimated_stage=stage,
                        evidence_sentence=sentence.strip(),
                        score=score,
                        url=page.url,
                        source_title=page.title,
                        source_domain=page.domain,
                        notes=notes,
                    )
                )

    return deduplicate_companies(extracted)


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(text) if part.strip()]


def normalize_company_name(name: str) -> str:
    compact = re.sub(r"\s+", " ", name).strip(" 　")
    segments = re.split(r"(?:として|にて|の|を|は|に|と)", compact)
    company_pattern = re.compile(
        r"([一-龠ぁ-んァ-ヴA-Za-z0-9・\-\(\)]+(?:株式会社|有限会社|合同会社|Inc\.|Co\., Ltd\.|Corporation|Company))"
    )
    for segment in reversed(segments):
        match = company_pattern.search(segment)
        if match:
            return match.group(1)
    company_matches = list(company_pattern.finditer(compact))
    if company_matches:
        return company_matches[-1].group(1)
    return compact


def classify_category(sentence: str, page: RawPage) -> tuple[str, float, list[str]]:
    lowered = sentence.lower()
    notes: list[str] = []
    score = 0.0

    if "代理店" in sentence or "authorized distributor" in lowered:
        notes.append("代理店キーワード")
        return "代理店", 0.32, notes
    if "販売店" in sentence or "dealer" in lowered:
        notes.append("販売店キーワード")
        return "販売店", 0.24, notes
    if "取扱店" in sentence or "取扱" in sentence:
        notes.append("取扱店キーワード")
        return "取扱店", 0.22, notes
    if "商社" in sentence or "trading" in lowered:
        notes.append("商社キーワード")
        return "商社", 0.28, notes

    if any(token in lowered for token in ["official", "公式", "partner"]):
        score += 0.08
        notes.append("公式/パートナー文脈")

    if page.domain.endswith(".co.jp"):
        score += 0.02

    return "不明", score, notes


def estimate_stage(
    sentence: str, page: RawPage, category: str
) -> tuple[str, float, list[str]]:
    lowered = sentence.lower()
    notes: list[str] = []
    score = 0.0

    if "公式" in page.title or "メーカー" in page.title or is_likely_manufacturer_domain(page):
        if "代理店" in sentence or "authorized distributor" in lowered:
            notes.append("メーカー公式掲載 + 代理店記述")
            return "一次代理店", 0.34, notes

    if category == "商社" or any(token in lowered for token in ["多数メーカー", "各社製品", "multi-brand"]):
        notes.append("複数メーカー取扱い文脈")
        return "二次商社", 0.26, notes

    if category in {"販売店", "取扱店"}:
        notes.append("販売/取扱店文脈")
        return "取扱店 / 販売店", 0.22, notes

    if "代理店" in sentence:
        notes.append("代理店キーワード優先")
        return "一次代理店", 0.18, notes

    return "不明", score, notes


def is_likely_manufacturer_domain(page: RawPage) -> bool:
    domain = page.domain.lower()
    title = page.title.lower()
    return any(token in domain or token in title for token in ["omron", "mitsubishi", "manufacturer", "公式"])


def classify_region(sentence: str, body: str) -> str:
    merged = f"{sentence} {body[:400]}".lower()
    for region, keywords in REGION_RULES.items():
        if any(keyword.lower() in merged for keyword in keywords):
            return region
    return "不明"


def deduplicate_companies(items: list[ExtractedCompany]) -> list[ExtractedCompany]:
    grouped: dict[tuple[str, str], list[ExtractedCompany]] = defaultdict(list)
    for item in items:
        grouped[(item.manufacturer_name, item.company_name)].append(item)

    deduped: list[ExtractedCompany] = []
    for _, group in grouped.items():
        best = sorted(group, key=lambda item: (item.score, len(item.evidence_sentence)), reverse=True)[0]
        deduped.append(best)
    return sorted(
        deduped,
        key=lambda item: (item.manufacturer_name, stage_rank(item.estimated_stage), -item.score, item.company_name),
    )


def stage_rank(stage: str) -> int:
    order = {
        "一次代理店": 0,
        "二次商社": 1,
        "取扱店 / 販売店": 2,
        "不明": 3,
    }
    return order.get(stage, 9)
