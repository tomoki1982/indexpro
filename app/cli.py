from __future__ import annotations

import argparse
from pathlib import Path

from .indexpro_directory_validation import run_validation
from .indexpro_directory_pipeline import run_indexpro_directory_pipeline
from .settings import AppSettings, INDEXPRO_LISTINGS_DIR, INDEXPRO_VALIDATION_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="indexPro 一覧収集と検証のための最小プロトタイプ"
    )
    parser.add_argument(
        "--mode",
        choices=[
            "indexpro-directory-fixture",
            "indexpro-directory-live",
            "indexpro-directory-validate",
        ],
        default="indexpro-directory-live",
        help="indexPro 全体一覧収集または検証を実行",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="SQLite 出力先。未指定時は output/supplier_flow.db",
    )
    parser.add_argument(
        "--crawl-delay",
        type=float,
        default=0.0,
        help="一覧巡回時のリクエスト間隔（秒）",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = AppSettings()
    if args.db_path:
        settings.database_path = args.db_path
    settings.crawl_delay_seconds = args.crawl_delay

    if args.mode in {"indexpro-directory-fixture", "indexpro-directory-live"}:
        result = run_indexpro_directory_pipeline(args.mode, settings)
        print("=== indexPro 一覧収集結果 ===")
        print(f"メーカー一覧数: {len(result.manufacturers)}")
        print(f"代理店・取扱店一覧数: {len(result.distributors)}")
        print(f"取扱メーカー関係数: {len(result.handlings)}")
        print(f"メーカー別関係数: {len(result.relations)}")
        print(f"生ページ数: {len(result.raw_pages)}")
        print("出力先:")
        print("  output/indexpro/listings/indexpro_directory_manufacturers.csv")
        print("  output/indexpro/listings/indexpro_directory_distributors.csv")
        print("  output/indexpro/listings/indexpro_directory_handlings.csv")
        print("  output/indexpro/listings/indexpro_directory_relations.csv")
        print("  output/indexpro/listings/indexpro_directory_metrics.csv")
        return

    if args.mode == "indexpro-directory-validate":
        summary = run_validation(INDEXPRO_LISTINGS_DIR, INDEXPRO_VALIDATION_DIR)
        print("=== indexPro 一覧検証結果 ===")
        print(f"代理店行数: {summary.distributor_rows}")
        print(f"ユニークdid数: {summary.unique_dids}")
        print(f"did重複グループ数: {summary.duplicate_did_groups}")
        print(f"代理店名表記ゆれ候補グループ数: {summary.distributor_name_variant_groups}")
        print(f"メーカー行数: {summary.manufacturer_rows}")
        print(f"取扱関係行数: {summary.handling_rows}")
        print(f"取扱メーカー名の完全一致数: {summary.handling_exact_matches}")
        print(f"取扱メーカー名の正規化一致数: {summary.handling_normalized_matches}")
        print(f"取扱メーカー名の未一致数: {summary.handling_unmatched}")
        print("出力先:")
        print("  output/indexpro/validation/indexpro_validation_summary.csv")
        print("  output/indexpro/validation/indexpro_validation_duplicate_dids.csv")
        print("  output/indexpro/validation/indexpro_validation_name_variants.csv")
        print("  output/indexpro/validation/indexpro_validation_match_metrics.csv")
        print("  output/indexpro/validation/indexpro_validation_unmatched_handlings.csv")
        return


if __name__ == "__main__":
    main()
