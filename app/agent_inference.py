from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


AGENT_TYPE = "代理店"
RETAILER_TYPE = "取扱店"


@dataclass(slots=True)
class CandidateAgentResult:
    rank: int
    agent_name: str
    score: float
    has_direct_connection: bool
    retailer_related_manufacturer_count: int
    matched_related_manufacturer_count: int
    agent_total_handling_count: int
    evidence_manufacturers: list[str]


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


def get_agents_by_manufacturer(relations: pd.DataFrame, manufacturer_name: str) -> pd.DataFrame:
    canonical_name = find_matching_name(relations["manufacturer_name"], manufacturer_name)
    if canonical_name is None:
        return relations.iloc[0:0].copy()
    rows = relations[
        (relations["manufacturer_name"] == canonical_name)
        & (relations["relation_category"] == AGENT_TYPE)
    ].copy()
    return rows.drop_duplicates(subset=["manufacturer_name", "distributor_name"])


def get_dealers_by_manufacturer(
    relations: pd.DataFrame,
    manufacturer_name: str,
    relation_type: str,
) -> pd.DataFrame:
    canonical_name = find_matching_name(relations["manufacturer_name"], manufacturer_name)
    if canonical_name is None:
        return relations.iloc[0:0].copy()
    rows = relations[
        (relations["manufacturer_name"] == canonical_name)
        & (relations["relation_category"] == relation_type)
    ].copy()
    return rows.drop_duplicates(subset=["manufacturer_name", "distributor_name"])


def get_manufacturers_by_dealer(
    relations: pd.DataFrame,
    company_name: str,
    relation_type: str,
) -> list[str]:
    canonical_name = find_matching_name(relations["distributor_name"], company_name)
    if canonical_name is None:
        return []
    rows = relations[
        (relations["distributor_name"] == canonical_name)
        & (relations["relation_category"] == relation_type)
    ].copy()
    return sorted(rows["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist())


def build_agent_total_handling_map(handlings: pd.DataFrame) -> dict[str, int]:
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


def get_candidate_agents_by_manufacturer_and_retailer(
    manufacturer_name: str,
    retailer_name: str,
    relations: pd.DataFrame,
    handlings: pd.DataFrame,
) -> list[CandidateAgentResult]:
    if relations.empty:
        return []

    normalized_relations = relations.copy()
    normalized_relations["manufacturer_name"] = normalized_relations["manufacturer_name"].astype(str)
    normalized_relations["distributor_name"] = normalized_relations["distributor_name"].astype(str)
    normalized_relations["relation_category"] = normalized_relations["relation_category"].astype(str)

    base_agents = get_agents_by_manufacturer(normalized_relations, manufacturer_name)
    if base_agents.empty:
        return []

    retailer_manufacturers = get_manufacturers_by_dealer(normalized_relations, retailer_name, RETAILER_TYPE)
    if not retailer_manufacturers:
        return []

    retailer_manufacturer_set = set(retailer_manufacturers)
    retailer_agent_rows = normalized_relations[
        (normalized_relations["manufacturer_name"].isin(retailer_manufacturer_set))
        & (normalized_relations["relation_category"] == AGENT_TYPE)
    ].copy()

    if retailer_agent_rows.empty:
        return []

    base_agent_names = set(base_agents["distributor_name"].drop_duplicates().tolist())
    retailer_agent_rows = retailer_agent_rows[retailer_agent_rows["distributor_name"].isin(base_agent_names)].copy()
    if retailer_agent_rows.empty:
        return []

    agent_total_handling_map = build_agent_total_handling_map(handlings)
    related_total = len(retailer_manufacturers)
    grouped = (
        retailer_agent_rows.groupby("distributor_name")["manufacturer_name"]
        .apply(lambda series: sorted(set(series.tolist())))
        .to_dict()
    )

    results: list[CandidateAgentResult] = []
    for agent_name, evidence in grouped.items():
        matched_count = len(evidence)
        score = matched_count / related_total if related_total else 0.0
        results.append(
            CandidateAgentResult(
                rank=0,
                agent_name=agent_name,
                score=score,
                has_direct_connection=agent_name in base_agent_names,
                retailer_related_manufacturer_count=related_total,
                matched_related_manufacturer_count=matched_count,
                agent_total_handling_count=agent_total_handling_map.get(agent_name, 0),
                evidence_manufacturers=evidence,
            )
        )

    results.sort(
        key=lambda item: (
            -item.score,
            -item.matched_related_manufacturer_count,
            item.agent_total_handling_count,
            item.agent_name,
        )
    )
    for index, item in enumerate(results, start=1):
        item.rank = index
    return results
