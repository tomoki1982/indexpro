from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


AGENT_TYPE = "代理店"


@dataclass(slots=True)
class CompetitorCandidateResult:
    rank: int
    candidate_manufacturer_name: str
    common_distributor_count: int
    base_manufacturer_distributor_count: int
    candidate_manufacturer_distributor_count: int
    basic_score: float
    similarity_score: float
    common_distributors: list[str]


def normalize_name(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def find_matching_name(values: pd.Series, query: str) -> str | None:
    normalized_query = normalize_name(query)
    if not normalized_query:
        return None
    for value in values.dropna().astype(str).drop_duplicates():
        if normalize_name(value) == normalized_query:
            return value
    return None


def build_distributor_total_handling_map(handlings: pd.DataFrame) -> dict[str, int]:
    if handlings.empty:
        return {}
    cleaned = handlings.dropna(subset=["distributor_name", "handling_manufacturer_name"]).copy()
    cleaned["distributor_name"] = cleaned["distributor_name"].astype(str)
    cleaned["handling_manufacturer_name"] = cleaned["handling_manufacturer_name"].astype(str)
    grouped = (
        cleaned.drop_duplicates(subset=["distributor_name", "handling_manufacturer_name"])
        .groupby("distributor_name")["handling_manufacturer_name"]
        .count()
    )
    return {str(name): int(count) for name, count in grouped.items()}


def get_distributors_by_manufacturer(
    relations: pd.DataFrame,
    manufacturer_name: str,
    *,
    relation_type: str = AGENT_TYPE,
) -> list[str]:
    canonical_name = find_matching_name(relations["manufacturer_name"], manufacturer_name)
    if canonical_name is None:
        return []
    rows = relations[
        (relations["manufacturer_name"] == canonical_name)
        & (relations["relation_category"] == relation_type)
    ].copy()
    return sorted(rows["distributor_name"].dropna().astype(str).drop_duplicates().tolist())


def get_manufacturers_by_distributor(
    relations: pd.DataFrame,
    distributor_name: str,
    *,
    relation_type: str = AGENT_TYPE,
) -> list[str]:
    canonical_name = find_matching_name(relations["distributor_name"], distributor_name)
    if canonical_name is None:
        return []
    rows = relations[
        (relations["distributor_name"] == canonical_name)
        & (relations["relation_category"] == relation_type)
    ].copy()
    return sorted(rows["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist())


def build_manufacturer_distributor_index(
    relations: pd.DataFrame,
    *,
    relation_type: str = AGENT_TYPE,
    max_handling_count: int | None = None,
    handlings: pd.DataFrame | None = None,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    filtered = relations.copy()
    filtered["manufacturer_name"] = filtered["manufacturer_name"].astype(str)
    filtered["distributor_name"] = filtered["distributor_name"].astype(str)
    filtered["relation_category"] = filtered["relation_category"].astype(str)
    filtered = filtered[filtered["relation_category"] == relation_type].copy()
    filtered = filtered.drop_duplicates(subset=["manufacturer_name", "distributor_name"])

    if max_handling_count is not None and handlings is not None and not handlings.empty:
        handling_map = build_distributor_total_handling_map(handlings)
        filtered = filtered[
            filtered["distributor_name"].map(lambda name: handling_map.get(str(name), 0) <= max_handling_count)
        ].copy()

    manufacturer_to_distributors: dict[str, set[str]] = {}
    distributor_to_manufacturers: dict[str, set[str]] = {}

    for row in filtered.itertuples(index=False):
        manufacturer_name = str(row.manufacturer_name)
        distributor_name = str(row.distributor_name)
        manufacturer_to_distributors.setdefault(manufacturer_name, set()).add(distributor_name)
        distributor_to_manufacturers.setdefault(distributor_name, set()).add(manufacturer_name)

    return manufacturer_to_distributors, distributor_to_manufacturers


def calculate_competitor_score(
    base_distributors: set[str],
    candidate_distributors: set[str],
) -> tuple[int, float, float]:
    common_distributors = base_distributors & candidate_distributors
    common_count = len(common_distributors)
    base_count = len(base_distributors)
    candidate_count = len(candidate_distributors)

    basic_score = common_count / base_count if base_count else 0.0
    denominator = base_count + candidate_count - common_count
    similarity_score = common_count / denominator if denominator else 0.0
    return common_count, basic_score, similarity_score


def get_competitor_candidates(
    manufacturer_name: str,
    relations: pd.DataFrame,
    handlings: pd.DataFrame,
    *,
    max_handling_count: int | None = None,
) -> list[CompetitorCandidateResult]:
    if relations.empty:
        return []

    manufacturer_to_distributors, distributor_to_manufacturers = build_manufacturer_distributor_index(
        relations,
        max_handling_count=max_handling_count,
        handlings=handlings,
    )
    canonical_name = find_matching_name(pd.Series(manufacturer_to_distributors.keys(), dtype="object"), manufacturer_name)
    if canonical_name is None:
        return []

    base_distributors = manufacturer_to_distributors.get(canonical_name, set())
    if not base_distributors:
        return []

    candidate_names: set[str] = set()
    for distributor_name in base_distributors:
        candidate_names.update(distributor_to_manufacturers.get(distributor_name, set()))
    candidate_names.discard(canonical_name)

    results: list[CompetitorCandidateResult] = []
    for candidate_name in candidate_names:
        candidate_distributors = manufacturer_to_distributors.get(candidate_name, set())
        common_count, basic_score, similarity_score = calculate_competitor_score(
            base_distributors,
            candidate_distributors,
        )
        if common_count == 0:
            continue
        common_distributors = sorted(base_distributors & candidate_distributors)
        results.append(
            CompetitorCandidateResult(
                rank=0,
                candidate_manufacturer_name=candidate_name,
                common_distributor_count=common_count,
                base_manufacturer_distributor_count=len(base_distributors),
                candidate_manufacturer_distributor_count=len(candidate_distributors),
                basic_score=basic_score,
                similarity_score=similarity_score,
                common_distributors=common_distributors,
            )
        )

    results.sort(
        key=lambda item: (
            -item.basic_score,
            -item.common_distributor_count,
            -item.similarity_score,
            item.candidate_manufacturer_name,
        )
    )
    for index, item in enumerate(results, start=1):
        item.rank = index
    return results
