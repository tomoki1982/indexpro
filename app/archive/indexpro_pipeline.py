from __future__ import annotations

from pathlib import Path

from .indexpro import fetch_indexpro_live, load_indexpro_fixture
from .indexpro_reporting import (
    build_indexpro_tree,
    write_indexpro_distributors_csv,
    write_indexpro_html,
    write_indexpro_products_csv,
    write_indexpro_structure_txt,
)
from .models import IndexProResult
from .settings import INDEXPRO_FIXTURE_PATH, LATEST_DIR, AppSettings, ensure_output_dirs
from .storage import SQLiteStorage


def run_indexpro_pipeline(
    mode: str, manufacturers: list[str], settings: AppSettings
) -> IndexProResult:
    ensure_output_dirs()
    storage = SQLiteStorage(settings.database_path)
    all_results: list[IndexProResult] = []

    try:
        for manufacturer in manufacturers:
            if mode == "indexpro-fixture":
                result = load_indexpro_fixture(INDEXPRO_FIXTURE_PATH, manufacturer)
            else:
                result = fetch_indexpro_live(manufacturer, settings)
            all_results.append(result)
            storage.save_raw_pages(result.raw_pages)
            storage.save_indexpro_result(result)

        merged = merge_indexpro_results(all_results)
        write_indexpro_structure_txt(LATEST_DIR / "indexpro_structure.txt", merged)
        write_indexpro_products_csv(LATEST_DIR / "indexpro_products.csv", merged.products)
        write_indexpro_distributors_csv(LATEST_DIR / "indexpro_distributors.csv", merged.distributors)
        write_indexpro_html(LATEST_DIR / "indexpro_report.html", merged)
        return merged
    finally:
        storage.close()


def merge_indexpro_results(results: list[IndexProResult]) -> IndexProResult:
    manufacturers = []
    products = []
    distributors = []
    raw_pages = []
    for result in results:
        manufacturers.extend(result.manufacturers)
        products.extend(result.products)
        distributors.extend(result.distributors)
        raw_pages.extend(result.raw_pages)
    return IndexProResult(
        manufacturers=manufacturers,
        products=products,
        distributors=distributors,
        raw_pages=raw_pages,
    )


def build_indexpro_summary(result: IndexProResult) -> str:
    return build_indexpro_tree(result)
