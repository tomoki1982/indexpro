from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path

from .models import ExtractedCompany


def write_list_csv(path: Path, items: list[ExtractedCompany]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "メーカー名",
                "会社名",
                "区分",
                "地域",
                "推定段階",
                "根拠文",
                "URL",
                "スコア",
                "ソースタイトル",
                "ドメイン",
            ]
        )
        for item in items:
            writer.writerow(
                [
                    item.manufacturer_name,
                    item.company_name,
                    item.company_category,
                    item.region,
                    item.estimated_stage,
                    item.evidence_sentence,
                    item.url,
                    item.score,
                    item.source_title,
                    item.source_domain,
                ]
            )


def build_tree_text(items: list[ExtractedCompany]) -> str:
    grouped: dict[str, list[ExtractedCompany]] = defaultdict(list)
    for item in items:
        grouped[item.manufacturer_name].append(item)

    lines: list[str] = []
    for manufacturer, group in grouped.items():
        lines.append(manufacturer)
        sorted_group = sorted(group, key=lambda x: (stage_order(x.estimated_stage), -x.score, x.company_name))
        for index, item in enumerate(sorted_group):
            branch = "└─" if index == len(sorted_group) - 1 else "├─"
            lines.append(
                f"  {branch} {item.company_name} [{item.estimated_stage} / {item.company_category} / {item.region}]"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_structure_txt(path: Path, items: list[ExtractedCompany]) -> None:
    path.write_text(build_tree_text(items), encoding="utf-8")


def write_html_report(path: Path, items: list[ExtractedCompany], tree_text: str) -> None:
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{escape(item.manufacturer_name)}</td>"
            f"<td>{escape(item.company_name)}</td>"
            f"<td>{escape(item.company_category)}</td>"
            f"<td>{escape(item.region)}</td>"
            f"<td>{escape(item.estimated_stage)}</td>"
            f"<td>{escape(item.evidence_sentence)}</td>"
            f"<td><a href='{escape(item.url)}'>{escape(item.url)}</a></td>"
            f"<td>{item.score:.2f}</td>"
            "</tr>"
        )

    html_body = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>仕入先商流プロトタイプ</title>
  <style>
    body {{ font-family: 'Yu Gothic UI', sans-serif; margin: 24px; background: #f6f8fb; color: #17212b; }}
    h1, h2 {{ margin-bottom: 12px; }}
    .panel {{ background: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 6px 20px rgba(19, 38, 62, 0.08); }}
    pre {{ white-space: pre-wrap; line-height: 1.6; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border: 1px solid #dce4ee; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ background: #eaf1f8; }}
    a {{ color: #0a66c2; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>仕入先商流プロトタイプ</h1>
    <p>成立性確認用の簡易レポートです。分類・段階はルールベースの仮推定です。</p>
  </div>
  <div class="panel">
    <h2>構造表示</h2>
    <pre>{escape(tree_text)}</pre>
  </div>
  <div class="panel">
    <h2>一覧表示</h2>
    <table>
      <thead>
        <tr>
          <th>メーカー名</th>
          <th>会社名</th>
          <th>区分</th>
          <th>地域</th>
          <th>推定段階</th>
          <th>根拠文</th>
          <th>URL</th>
          <th>スコア</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    path.write_text(html_body, encoding="utf-8")


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def stage_order(stage: str) -> int:
    mapping = {
        "一次代理店": 0,
        "二次商社": 1,
        "取扱店 / 販売店": 2,
        "不明": 3,
    }
    return mapping.get(stage, 9)

