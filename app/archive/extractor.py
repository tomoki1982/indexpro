from __future__ import annotations

from .classifier import extract_companies
from .models import ExtractedCompany, RawPage


def run_extraction(raw_pages: list[RawPage]) -> list[ExtractedCompany]:
    return extract_companies(raw_pages)

