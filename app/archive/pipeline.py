from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .extractor import run_extraction
from .fetcher import fetch_pages, load_fixture_pages
from .models import ExtractedCompany, RawPage
from .reporting import build_tree_text, write_html_report, write_list_csv, write_structure_txt
from .search import load_fixture_candidates, search_with_duckduckgo
from .settings import AppSettings, FIXTURE_PATH, LATEST_DIR, ensure_output_dirs
from .storage import SQLiteStorage


@dataclass(slots=True)
class PipelineResult:
    raw_pages: list[RawPage]
    extracted_companies: list[ExtractedCompany]
    structure_text: str


def load_manufacturers(input_csv: Path | None, inline_manufacturers: list[str]) -> list[str]:
    manufacturers: list[str] = []
    if input_csv:
        with input_csv.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                value = (row.get("manufacturer_name") or "").strip()
                if value:
                    manufacturers.append(value)
    manufacturers.extend(item.strip() for item in inline_manufacturers if item.strip())
    unique: list[str] = []
    seen: set[str] = set()
    for item in manufacturers:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def run_pipeline(
    mode: str,
    manufacturers: list[str],
    settings: AppSettings,
) -> PipelineResult:
    ensure_output_dirs()
    storage = SQLiteStorage(settings.database_path)

    try:
        raw_pages: list[RawPage] = []
        for manufacturer in manufacturers:
            if mode == "fixture":
                _ = load_fixture_candidates(FIXTURE_PATH, manufacturer)
                pages = load_fixture_pages(FIXTURE_PATH, manufacturer)
            else:
                candidates = search_with_duckduckgo(manufacturer, settings)
                pages = fetch_pages(candidates, settings)
            raw_pages.extend(pages)

        extracted_companies = run_extraction(raw_pages)

        storage.save_raw_pages(raw_pages)
        storage.save_extracted_companies(extracted_companies)

        structure_text = build_tree_text(extracted_companies)
        write_structure_txt(LATEST_DIR / "structure.txt", extracted_companies)
        write_list_csv(LATEST_DIR / "list.csv", extracted_companies)
        write_html_report(LATEST_DIR / "report.html", extracted_companies, structure_text)

        return PipelineResult(
            raw_pages=raw_pages,
            extracted_companies=extracted_companies,
            structure_text=structure_text,
        )
    finally:
        storage.close()

