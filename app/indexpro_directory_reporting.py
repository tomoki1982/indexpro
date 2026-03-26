from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .indexpro_directory import IndexProDirectoryResult


def write_directory_outputs(base_dir: Path, result: IndexProDirectoryResult) -> None:
    write_manufacturers_csv(base_dir / "indexpro_directory_manufacturers.csv", result)
    write_distributors_csv(base_dir / "indexpro_directory_distributors.csv", result)
    write_handlings_csv(base_dir / "indexpro_directory_handlings.csv", result)
    write_relations_csv(base_dir / "indexpro_directory_relations.csv", result)
    write_metrics_csv(base_dir / "indexpro_directory_metrics.csv", result)


def write_manufacturers_csv(path: Path, result: IndexProDirectoryResult) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["manufacturer_name", "initial", "mcid", "distributor_list_url"])
        for item in result.manufacturers:
            writer.writerow([item.name, item.initial, item.mcid, item.distributor_list_url])


def write_distributors_csv(path: Path, result: IndexProDirectoryResult) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "distributor_name",
                "initial",
                "did",
                "source_category",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        )
        for item in result.distributors:
            writer.writerow(
                [
                    item.name,
                    item.initial,
                    item.did,
                    item.source_category,
                    item.company_url,
                    item.location_url,
                    item.online_sales_url,
                    item.handling_makers_url,
                ]
            )


def write_handlings_csv(path: Path, result: IndexProDirectoryResult) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["did", "distributor_name", "handling_manufacturer_name"])
        for item in result.handlings:
            writer.writerow([item.did, item.distributor_name, item.handling_manufacturer_name])


def write_relations_csv(path: Path, result: IndexProDirectoryResult) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "mcid",
                "manufacturer_name",
                "distributor_name",
                "did",
                "relation_category",
                "company_url",
                "location_url",
                "online_sales_url",
            ]
        )
        for item in result.relations:
            writer.writerow(
                [
                    item.mcid,
                    item.manufacturer_name,
                    item.distributor_name,
                    item.did,
                    item.relation_category,
                    item.company_url,
                    item.location_url,
                    item.online_sales_url,
                ]
            )


def write_metrics_csv(path: Path, result: IndexProDirectoryResult) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric_name", "metric_value"])
        writer.writerow(["generated_at", datetime.now().isoformat()])
        writer.writerow(["manufacturer_count", len(result.manufacturers)])
        writer.writerow(["distributor_count", len(result.distributors)])
        writer.writerow(["handling_relation_count", len(result.handlings)])
        writer.writerow(["manufacturer_distributor_relation_count", len(result.relations)])
