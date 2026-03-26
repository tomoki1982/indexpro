from __future__ import annotations

import csv
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ValidationSummary:
    distributor_rows: int
    unique_dids: int
    duplicate_did_rows: int
    duplicate_did_groups: int
    distributor_name_variant_groups: int
    manufacturer_rows: int
    unique_manufacturer_names: int
    handling_rows: int
    handling_exact_matches: int
    handling_normalized_matches: int
    handling_unmatched: int


def run_validation(listings_dir: Path, validation_dir: Path) -> ValidationSummary:
    manufacturers = read_csv(listings_dir / "indexpro_directory_manufacturers.csv")
    distributors = read_csv(listings_dir / "indexpro_directory_distributors.csv")
    handlings = read_csv(listings_dir / "indexpro_directory_handlings.csv")

    duplicate_dids = analyze_duplicate_dids(distributors)
    name_variants = analyze_name_variants(distributors)
    match_result = analyze_manufacturer_matches(manufacturers, handlings)

    write_csv(validation_dir / "indexpro_validation_duplicate_dids.csv", duplicate_dids)
    write_csv(validation_dir / "indexpro_validation_name_variants.csv", name_variants)
    write_csv(
        validation_dir / "indexpro_validation_unmatched_handlings.csv",
        match_result["unmatched_rows"],
    )
    write_csv(
        validation_dir / "indexpro_validation_match_metrics.csv",
        match_result["metrics_rows"],
    )

    distributor_rows = len(distributors)
    unique_dids = len({row["did"] for row in distributors})
    duplicate_did_rows = sum(int(row["row_count"]) for row in duplicate_dids)
    duplicate_did_groups = len(duplicate_dids)
    distributor_name_variant_groups = len(name_variants)
    manufacturer_rows = len(manufacturers)
    unique_manufacturer_names = len({row["manufacturer_name"] for row in manufacturers})
    handling_rows = len(handlings)
    handling_exact_matches = int(match_result["summary"]["handling_exact_matches"])
    handling_normalized_matches = int(match_result["summary"]["handling_normalized_matches"])
    handling_unmatched = int(match_result["summary"]["handling_unmatched"])

    summary = ValidationSummary(
        distributor_rows=distributor_rows,
        unique_dids=unique_dids,
        duplicate_did_rows=duplicate_did_rows,
        duplicate_did_groups=duplicate_did_groups,
        distributor_name_variant_groups=distributor_name_variant_groups,
        manufacturer_rows=manufacturer_rows,
        unique_manufacturer_names=unique_manufacturer_names,
        handling_rows=handling_rows,
        handling_exact_matches=handling_exact_matches,
        handling_normalized_matches=handling_normalized_matches,
        handling_unmatched=handling_unmatched,
    )
    write_summary_csv(validation_dir / "indexpro_validation_summary.csv", summary)
    return summary


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            handle.write("")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(path: Path, summary: ValidationSummary) -> None:
    rows = [
        {"metric_name": "distributor_rows", "metric_value": str(summary.distributor_rows)},
        {"metric_name": "unique_dids", "metric_value": str(summary.unique_dids)},
        {"metric_name": "duplicate_did_rows", "metric_value": str(summary.duplicate_did_rows)},
        {"metric_name": "duplicate_did_groups", "metric_value": str(summary.duplicate_did_groups)},
        {
            "metric_name": "distributor_name_variant_groups",
            "metric_value": str(summary.distributor_name_variant_groups),
        },
        {"metric_name": "manufacturer_rows", "metric_value": str(summary.manufacturer_rows)},
        {
            "metric_name": "unique_manufacturer_names",
            "metric_value": str(summary.unique_manufacturer_names),
        },
        {"metric_name": "handling_rows", "metric_value": str(summary.handling_rows)},
        {
            "metric_name": "handling_exact_matches",
            "metric_value": str(summary.handling_exact_matches),
        },
        {
            "metric_name": "handling_normalized_matches",
            "metric_value": str(summary.handling_normalized_matches),
        },
        {"metric_name": "handling_unmatched", "metric_value": str(summary.handling_unmatched)},
    ]
    write_csv(path, rows)


def analyze_duplicate_dids(distributors: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in distributors:
        groups[row["did"]].append(row)

    result: list[dict[str, str]] = []
    for did, rows in groups.items():
        if len(rows) <= 1:
            continue
        names = sorted({row["distributor_name"] for row in rows})
        urls = sorted({row["company_url"] for row in rows})
        result.append(
            {
                "did": did,
                "row_count": str(len(rows)),
                "distributor_names": " | ".join(names),
                "company_urls": " | ".join(urls),
            }
        )
    return sorted(result, key=lambda row: (-int(row["row_count"]), row["did"]))


def analyze_name_variants(distributors: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in distributors:
        groups[normalize_company_name(row["distributor_name"])].append(row)

    result: list[dict[str, str]] = []
    for normalized_name, rows in groups.items():
        raw_names = sorted({row["distributor_name"] for row in rows})
        dids = sorted({row["did"] for row in rows})
        if len(raw_names) <= 1:
            continue
        result.append(
            {
                "normalized_name": normalized_name,
                "variant_count": str(len(raw_names)),
                "did_count": str(len(dids)),
                "raw_names": " | ".join(raw_names),
                "dids": " | ".join(dids),
            }
        )
    return sorted(result, key=lambda row: (-int(row["variant_count"]), row["normalized_name"]))


def analyze_manufacturer_matches(
    manufacturers: list[dict[str, str]], handlings: list[dict[str, str]]
) -> dict[str, object]:
    manufacturer_names = {row["manufacturer_name"] for row in manufacturers}
    normalized_map: dict[str, list[str]] = defaultdict(list)
    for name in manufacturer_names:
        normalized_map[normalize_manufacturer_name(name)].append(name)

    exact_matches = 0
    normalized_matches = 0
    unmatched_rows: list[dict[str, str]] = []
    unmatched_counter: Counter[str] = Counter()

    for row in handlings:
        handling_name = row["handling_manufacturer_name"]
        if handling_name in manufacturer_names:
            exact_matches += 1
            continue
        normalized_name = normalize_manufacturer_name(handling_name)
        matched = normalized_map.get(normalized_name, [])
        if matched:
            normalized_matches += 1
            continue
        unmatched_counter[handling_name] += 1

    for handling_name, count in unmatched_counter.most_common():
        normalized_name = normalize_manufacturer_name(handling_name)
        candidates = suggest_candidates(normalized_name, normalized_map)
        unmatched_rows.append(
            {
                "handling_manufacturer_name": handling_name,
                "occurrence_count": str(count),
                "normalized_name": normalized_name,
                "candidate_manufacturers": " | ".join(candidates[:5]),
            }
        )

    metrics_rows = [
        {"metric_name": "manufacturer_name_count", "metric_value": str(len(manufacturer_names))},
        {"metric_name": "handling_row_count", "metric_value": str(len(handlings))},
        {"metric_name": "handling_exact_matches", "metric_value": str(exact_matches)},
        {"metric_name": "handling_normalized_matches", "metric_value": str(normalized_matches)},
        {
            "metric_name": "handling_matched_total",
            "metric_value": str(exact_matches + normalized_matches),
        },
        {
            "metric_name": "handling_unmatched",
            "metric_value": str(len(handlings) - exact_matches - normalized_matches),
        },
    ]

    return {
        "summary": {
            "handling_exact_matches": exact_matches,
            "handling_normalized_matches": normalized_matches,
            "handling_unmatched": len(handlings) - exact_matches - normalized_matches,
        },
        "metrics_rows": metrics_rows,
        "unmatched_rows": unmatched_rows,
    }


def normalize_company_name(value: str) -> str:
    text = normalize_text(value)
    for token in ["株式会社", "有限会社", "合同会社", "(株)", "（株）", "Inc.", "Co., Ltd."]:
        text = text.replace(token, "")
    return text


def normalize_manufacturer_name(value: str) -> str:
    text = normalize_text(value)
    replacements = [
        " 制御機器・FAシステム",
        " 電子部品",
        "株式会社",
        "有限会社",
        "合同会社",
        "(株)",
        "（株）",
        "inc.",
        "co.,ltd.",
        "co., ltd.",
    ]
    lowered = text.lower()
    for token in replacements:
        lowered = lowered.replace(token.lower(), "")
    return lowered


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).strip().lower()
    for token in [" ", "\u3000", "-", "‐", "‑", "–", "—", "・", "/", "／", "(", ")", "（", "）", ",", "."]:
        text = text.replace(token, "")
    return text


def suggest_candidates(normalized_name: str, normalized_map: dict[str, list[str]]) -> list[str]:
    suggestions: list[str] = []
    for key, names in normalized_map.items():
        if not normalized_name or not key:
            continue
        if normalized_name in key or key in normalized_name:
            suggestions.extend(names)
        if len(suggestions) >= 10:
            break
    return sorted(dict.fromkeys(suggestions))
