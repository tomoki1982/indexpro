from __future__ import annotations

import csv
import html
from pathlib import Path

from .models import IndexProDistributor, IndexProProduct, IndexProResult


def build_indexpro_tree(result: IndexProResult) -> str:
    lines: list[str] = []
    for manufacturer in result.manufacturers:
        lines.append(manufacturer.display_name)
        distributors = sorted(
            [item for item in result.distributors if item.manufacturer_name == manufacturer.manufacturer_name],
            key=lambda item: (-len(item.handling_manufacturers), item.distributor_name),
        )
        for index, distributor in enumerate(distributors):
            branch = "└─" if index == len(distributors) - 1 else "├─"
            tail = f" [{distributor.distributor_type} / {distributor.region} / 取扱メーカー{len(distributor.handling_manufacturers)}社]"
            lines.append(f"  {branch} {distributor.distributor_name}{tail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_indexpro_products_csv(path: Path, products: list[IndexProProduct]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["メーカー名", "製品名", "カテゴリ", "要約", "URL"])
        for item in products:
            writer.writerow(
                [
                    item.manufacturer_name,
                    item.product_name,
                    item.category,
                    item.summary,
                    item.product_url,
                ]
            )


def write_indexpro_distributors_csv(path: Path, distributors: list[IndexProDistributor]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "メーカー名",
                "代理店・取扱店名",
                "区分",
                "地域",
                "掲載根拠",
                "代理店URL",
                "拠点URL",
                "取扱メーカーURL",
                "取扱メーカー数",
                "取扱メーカー一覧",
            ]
        )
        for item in distributors:
            writer.writerow(
                [
                    item.manufacturer_name,
                    item.distributor_name,
                    item.distributor_type,
                    item.region,
                    item.evidence,
                    item.distributor_url,
                    item.location_url,
                    item.handling_makers_url,
                    len(item.handling_manufacturers),
                    " | ".join(item.handling_manufacturers),
                ]
            )


def write_indexpro_structure_txt(path: Path, result: IndexProResult) -> None:
    path.write_text(build_indexpro_tree(result), encoding="utf-8")


def write_indexpro_html(path: Path, result: IndexProResult) -> None:
    tree_text = build_indexpro_tree(result)
    product_rows = "".join(
        [
            "<tr>"
            f"<td>{escape(item.manufacturer_name)}</td>"
            f"<td>{escape(item.product_name)}</td>"
            f"<td>{escape(item.category)}</td>"
            f"<td>{escape(item.summary)}</td>"
            f"<td><a href='{escape(item.product_url)}'>{escape(item.product_url)}</a></td>"
            "</tr>"
            for item in result.products
        ]
    )
    distributor_rows = "".join(
        [
            "<tr>"
            f"<td>{escape(item.manufacturer_name)}</td>"
            f"<td>{escape(item.distributor_name)}</td>"
            f"<td>{escape(item.distributor_type)}</td>"
            f"<td>{escape(item.region)}</td>"
            f"<td>{escape(item.evidence)}</td>"
            f"<td>{len(item.handling_manufacturers)}</td>"
            f"<td>{escape(' | '.join(item.handling_manufacturers[:20]))}</td>"
            f"<td><a href='{escape(item.handling_makers_url)}'>{escape(item.handling_makers_url)}</a></td>"
            "</tr>"
            for item in result.distributors
        ]
    )

    body = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>indexPro 仕入先抽出プロトタイプ</title>
  <style>
    body {{ font-family: 'Yu Gothic UI', sans-serif; margin: 24px; background: #f6f8fb; color: #17212b; }}
    .panel {{ background: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 6px 20px rgba(19, 38, 62, 0.08); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #dce4ee; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ background: #eaf1f8; }}
    pre {{ white-space: pre-wrap; line-height: 1.6; }}
    a {{ color: #0a66c2; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>indexPro 仕入先抽出プロトタイプ</h1>
    <p>indexPro 掲載情報だけを対象に、メーカー・製品情報・代理店/取扱店・代理店側の取扱メーカーを整理したレポートです。</p>
  </div>
  <div class="panel">
    <h2>構造表示</h2>
    <pre>{escape(tree_text)}</pre>
  </div>
  <div class="panel">
    <h2>製品情報</h2>
    <table>
      <thead>
        <tr><th>メーカー名</th><th>製品名</th><th>カテゴリ</th><th>要約</th><th>URL</th></tr>
      </thead>
      <tbody>{product_rows}</tbody>
    </table>
  </div>
  <div class="panel">
    <h2>代理店・取扱店一覧</h2>
    <table>
      <thead>
        <tr><th>メーカー名</th><th>代理店・取扱店名</th><th>区分</th><th>地域</th><th>掲載根拠</th><th>取扱メーカー数</th><th>取扱メーカー一覧</th><th>取扱メーカーURL</th></tr>
      </thead>
      <tbody>{distributor_rows}</tbody>
    </table>
  </div>
</body>
</html>
"""
    path.write_text(body, encoding="utf-8")


def escape(value: str) -> str:
    return html.escape(value, quote=True)
