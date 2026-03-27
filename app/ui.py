from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError

import pandas as pd
import streamlit as st

try:
    from .agent_inference import get_candidate_agents_by_manufacturer_and_retailer
    from .competitor_inference import get_competitor_candidates
    from .settings import (
        INDEXPRO_DIRECTORY_DISTRIBUTORS_SOURCE,
        INDEXPRO_DIRECTORY_HANDLINGS_SOURCE,
        INDEXPRO_DIRECTORY_MANUFACTURERS_SOURCE,
        INDEXPRO_DIRECTORY_METRICS_SOURCE,
        INDEXPRO_DIRECTORY_RELATIONS_SOURCE,
        INDEXPRO_LISTINGS_DIR,
        INDEXPRO_VALIDATION_DIR,
    )
except ImportError:
    import sys

    CURRENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_DIR.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from app.agent_inference import get_candidate_agents_by_manufacturer_and_retailer
    from app.competitor_inference import get_competitor_candidates
    from app.settings import (
        INDEXPRO_DIRECTORY_DISTRIBUTORS_SOURCE,
        INDEXPRO_DIRECTORY_HANDLINGS_SOURCE,
        INDEXPRO_DIRECTORY_MANUFACTURERS_SOURCE,
        INDEXPRO_DIRECTORY_METRICS_SOURCE,
        INDEXPRO_DIRECTORY_RELATIONS_SOURCE,
        INDEXPRO_LISTINGS_DIR,
        INDEXPRO_VALIDATION_DIR,
    )


LOCAL_MANUFACTURERS_CSV = INDEXPRO_LISTINGS_DIR / "indexpro_directory_manufacturers.csv"
LOCAL_DISTRIBUTORS_CSV = INDEXPRO_LISTINGS_DIR / "indexpro_directory_distributors.csv"
LOCAL_HANDLINGS_CSV = INDEXPRO_LISTINGS_DIR / "indexpro_directory_handlings.csv"
LOCAL_RELATIONS_CSV = INDEXPRO_LISTINGS_DIR / "indexpro_directory_relations.csv"
LOCAL_METRICS_CSV = INDEXPRO_LISTINGS_DIR / "indexpro_directory_metrics.csv"

MANUFACTURERS_CSV = INDEXPRO_DIRECTORY_MANUFACTURERS_SOURCE
DISTRIBUTORS_CSV = INDEXPRO_DIRECTORY_DISTRIBUTORS_SOURCE
HANDLINGS_CSV = INDEXPRO_DIRECTORY_HANDLINGS_SOURCE
RELATIONS_CSV = INDEXPRO_DIRECTORY_RELATIONS_SOURCE
METRICS_CSV = INDEXPRO_DIRECTORY_METRICS_SOURCE
VALIDATION_SUMMARY_CSV = INDEXPRO_VALIDATION_DIR / "indexpro_validation_summary.csv"
LABELS_CSV = INDEXPRO_LISTINGS_DIR / "indexpro_directory_labels.csv"

CATEGORY_FILTER_OPTIONS = ["代理店", "取扱店", "オンライン販売"]
MANUAL_CATEGORY_OPTIONS = ["未設定", *CATEGORY_FILTER_OPTIONS]
REVIEW_STATUS_OPTIONS = ["未設定", "要確認", "有力候補", "既存取引あり"]
COMPANY_TYPE_OPTIONS = ["メーカー", "代理店", "取扱店", "オンライン販売"]

UNIFIED_EXPORT_COLUMNS = [
    "search_type",
    "search_query",
    "entity_type",
    "entity_name",
    "company_type",
    "manufacturer_name",
    "distributor_name",
    "relation_category",
    "classification",
    "review_status",
    "memo",
    "initial",
    "company_url",
    "location_url",
    "online_sales_url",
    "handling_makers_url",
    "manufacturer_page_url",
]

COMPANY_STATE_KEYS = [
    "company_query",
    "company_type_filter",
    "company_editor_target",
    "company_editor_category",
    "company_editor_status",
    "company_editor_memo",
]
MANUFACTURER_STATE_KEYS = [
    "manufacturer_query",
    "manufacturer_selected",
    "manufacturer_distributor_filter",
    "manufacturer_category_filter",
]
DISTRIBUTOR_STATE_KEYS = [
    "distributor_query",
    "distributor_selected",
    "distributor_relation_filter",
]
INFERENCE_STATE_KEYS = [
    "inference_manufacturer_query",
    "inference_retailer_query",
]
COMPETITOR_STATE_KEYS = [
    "competitor_manufacturer_query",
    "competitor_max_handling_enabled",
    "competitor_max_handling_count",
    "competitor_candidate_filter",
]


def is_remote_source(path_or_url: str | Path) -> bool:
    return str(path_or_url).startswith("http://") or str(path_or_url).startswith("https://")


@st.cache_data(show_spinner=False)
def load_csv(path_or_url: str | Path) -> pd.DataFrame:
    return pd.read_csv(path_or_url, encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def load_csv_with_fallback(primary: str | Path, fallback: Path | None = None) -> pd.DataFrame:
    try:
        return load_csv(primary)
    except (HTTPError, URLError, OSError, ValueError):
        if fallback is not None and fallback.exists():
            return load_csv(fallback)
        raise


@st.cache_data(show_spinner=False)
def load_labels() -> pd.DataFrame:
    if not LABELS_CSV.exists():
        return pd.DataFrame(
            columns=[
                "entity_type",
                "entity_name",
                "classification",
                "review_status",
                "memo",
                "updated_at",
            ]
        )

    frame = pd.read_csv(LABELS_CSV, encoding="utf-8-sig")

    if "entity_type" not in frame.columns:
        frame["entity_type"] = frame["did"].apply(lambda _: "distributor") if "did" in frame.columns else "distributor"
    if "entity_name" not in frame.columns:
        frame["entity_name"] = frame.get("distributor_name", "")
    if "classification" not in frame.columns:
        frame["classification"] = "未設定"
    if "review_status" not in frame.columns:
        frame["review_status"] = "未設定"
    if "memo" not in frame.columns:
        frame["memo"] = ""

    frame["entity_type"] = frame["entity_type"].fillna("").astype(str)
    frame["entity_name"] = frame["entity_name"].fillna("").astype(str)
    frame["classification"] = frame["classification"].apply(normalize_manual_category)
    frame["review_status"] = frame["review_status"].apply(normalize_review_status)
    frame["memo"] = frame["memo"].fillna("").astype(str)
    return frame[
        ["entity_type", "entity_name", "classification", "review_status", "memo", "updated_at"]
    ].drop_duplicates(subset=["entity_type", "entity_name"], keep="last")


@st.cache_data(show_spinner=False)
def load_app_data() -> dict[str, pd.DataFrame]:
    return {
        "manufacturers": load_csv_with_fallback(MANUFACTURERS_CSV, LOCAL_MANUFACTURERS_CSV),
        "distributors": load_csv_with_fallback(DISTRIBUTORS_CSV, LOCAL_DISTRIBUTORS_CSV),
        "handlings": load_csv_with_fallback(HANDLINGS_CSV, LOCAL_HANDLINGS_CSV),
        "relations": load_csv_with_fallback(RELATIONS_CSV, LOCAL_RELATIONS_CSV)
        if is_remote_source(RELATIONS_CSV) or LOCAL_RELATIONS_CSV.exists()
        else pd.DataFrame(),
        "metrics": load_csv_with_fallback(METRICS_CSV, LOCAL_METRICS_CSV)
        if is_remote_source(METRICS_CSV) or LOCAL_METRICS_CSV.exists()
        else pd.DataFrame(),
        "validation": load_csv(VALIDATION_SUMMARY_CSV) if VALIDATION_SUMMARY_CSV.exists() else pd.DataFrame(),
        "labels": load_labels(),
    }


def normalize_manual_category(value: object) -> str:
    text = str(value).strip() if value is not None else ""
    if text in MANUAL_CATEGORY_OPTIONS:
        return text
    if text in {"代理店・取扱店", "代理店"}:
        return "代理店"
    if text == "取扱店":
        return "取扱店"
    if text in {"オンライン", "Web", "オンライン販売"}:
        return "オンライン販売"
    return "未設定"


def normalize_review_status(value: object) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text in REVIEW_STATUS_OPTIONS else "未設定"


def default_category_from_source(source_category: object) -> str:
    return "オンライン販売" if str(source_category).strip() == "オンライン販売" else "未設定"


def entity_key(entity_type: str, entity_name: str) -> str:
    return f"{entity_type}:{entity_name}"


def save_labels(frame: pd.DataFrame) -> None:
    output = frame.copy()
    output["classification"] = output["classification"].apply(normalize_manual_category)
    output["review_status"] = output["review_status"].apply(normalize_review_status)
    output["memo"] = output["memo"].fillna("").astype(str)
    output.to_csv(LABELS_CSV, index=False, encoding="utf-8-sig")
    load_labels.clear()
    load_app_data.clear()


def render_candidate_agent_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("メーカー × 取扱店から推定代理店を探す")

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    manufacturer_options = [""] + sorted(
        manufacturers["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist()
    )

    relations = data["relations"].copy()
    retailer_options = [""]
    if not relations.empty:
        retailer_options += sorted(
            relations.loc[
                relations["relation_category"].astype(str) == "取扱店",
                "distributor_name",
            ]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

    input_col1, input_col2, button_col = st.columns([3, 3, 1])
    with input_col1:
        manufacturer_query = st.selectbox(
            "メーカー名",
            manufacturer_options,
            index=0,
            key="inference_manufacturer_query",
            format_func=lambda value: value or "選択してください",
        )
    with input_col2:
        retailer_query = st.selectbox(
            "取扱店名",
            retailer_options,
            index=0,
            key="inference_retailer_query",
            format_func=lambda value: value or "選択してください",
        )
    with button_col:
        st.write("")
        if st.button("クリア", key="inference_clear"):
            reset_form(INFERENCE_STATE_KEYS)
            st.rerun()

    manufacturer_query = str(manufacturer_query).strip()
    retailer_query = str(retailer_query).strip()
    search_clicked = st.button("検索", key="inference_search")

    if not manufacturer_query and not retailer_query:
        st.info("メーカー名と取扱店名を選択すると、両方に関係しそうな代理店候補を表示します。")
        return

    if not manufacturer_query or not retailer_query:
        st.info("メーカー名と取扱店名の両方を選択してください。")
        return

    if not search_clicked:
        st.caption("検索ボタンを押すと、取扱店側の関連メーカーとメーカー直下の代理店を突き合わせて候補を出します。")
        return

    results = get_candidate_agents_by_manufacturer_and_retailer(
        manufacturer_query,
        retailer_query,
        data["relations"],
        data["handlings"],
    )

    if not results:
        st.warning("推定代理店候補は0件でした。条件を変えて再度確認してください。")
        return

    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    result_frame = pd.DataFrame(
        [
            {
                "順位": item.rank,
                "代理店名": item.agent_name,
                "基本スコア": f"{item.score:.2f}",
                "score_value": item.score,
                "メーカーとの直接接続有無": "true" if item.has_direct_connection else "false",
                "取扱店側関連メーカー数": item.retailer_related_manufacturer_count,
                "関連メーカー件数": item.matched_related_manufacturer_count,
                "代理店総取扱メーカー数": item.agent_total_handling_count,
                "関連メーカー一覧": ", ".join(item.evidence_manufacturers),
            }
            for item in results
        ]
    )
    result_frame = result_frame.merge(
        distributors[
            [
                "distributor_name",
                "classification",
                "review_status",
                "memo",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        ].drop_duplicates(subset=["distributor_name"]),
        how="left",
        left_on="代理店名",
        right_on="distributor_name",
    )
    result_frame["classification"] = result_frame["classification"].fillna("")
    result_frame["review_status"] = result_frame["review_status"].fillna("")
    result_frame["memo"] = result_frame["memo"].fillna("")

    st.write(f"推定代理店候補: {len(result_frame)}件")
    render_link_table(
        result_frame[
            [
                "順位",
                "代理店名",
                "基本スコア",
                "メーカーとの直接接続有無",
                "取扱店側関連メーカー数",
                "関連メーカー件数",
                "代理店総取扱メーカー数",
                "関連メーカー一覧",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        ],
        link_columns={
            "company_url": "会社URL",
            "location_url": "営業拠点URL",
            "online_sales_url": "オンライン販売URL",
            "handling_makers_url": "取扱メーカーURL",
        },
    )

    export_frame = result_frame[
        [
            "順位",
            "代理店名",
            "基本スコア",
            "メーカーとの直接接続有無",
            "取扱店側関連メーカー数",
            "関連メーカー件数",
            "代理店総取扱メーカー数",
            "関連メーカー一覧",
            "classification",
            "review_status",
            "memo",
            "company_url",
            "location_url",
            "online_sales_url",
            "handling_makers_url",
        ]
    ].rename(
        columns={
            "classification": "区分",
            "review_status": "ステータス",
            "memo": "メモ",
            "company_url": "会社URL",
            "location_url": "営業拠点URL",
            "online_sales_url": "オンライン販売URL",
            "handling_makers_url": "取扱メーカーURL",
        }
    )
    render_unified_download(export_frame, file_name="candidate_agents_results.csv")


def main() -> None:
    st.set_page_config(
        page_title="indexPro 仕入先検索",
        page_icon=":material/account_tree:",
        layout="wide",
    )

    st.title("indexPro 仕入先検索")
    st.caption("企業検索、メーカー検索、代理店・取扱店検索を1つの画面で確認できます。")

    missing = find_missing_files()
    if missing:
        st.error("必要なCSVが見つかりません。先に一覧収集を実行してください。")
        for path in missing:
            st.code(str(path))
        st.stop()

    data = load_app_data()
    render_summary(data)

    tab1, tab2, tab3 = st.tabs(["企業検索", "メーカー検索", "代理店・取扱店検索"])
    with tab1:
        render_company_lookup(data)
    with tab2:
        render_manufacturer_lookup(data)
    with tab3:
        render_distributor_lookup(data)


def find_missing_files() -> list[Path]:
    required = [
        (MANUFACTURERS_CSV, LOCAL_MANUFACTURERS_CSV),
        (DISTRIBUTORS_CSV, LOCAL_DISTRIBUTORS_CSV),
        (HANDLINGS_CSV, LOCAL_HANDLINGS_CSV),
    ]
    missing: list[Path] = []
    for primary, fallback in required:
        if is_remote_source(primary):
            if fallback.exists():
                continue
            continue
        if not Path(primary).exists():
            missing.append(Path(primary))
    return missing


def render_summary(data: dict[str, pd.DataFrame]) -> None:
    metrics = metrics_to_map(data["metrics"])
    validation = metrics_to_map(data["validation"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("メーカー数", metrics.get("manufacturer_count", "-"))
    col2.metric("代理店数", metrics.get("distributor_count", "-"))
    col3.metric("取扱関係数", metrics.get("handling_relation_count", "-"))
    col4.metric("未一致件数", validation.get("handling_unmatched", "-"))


def metrics_to_map(frame: pd.DataFrame) -> dict[str, str]:
    if frame.empty or not {"metric_name", "metric_value"}.issubset(frame.columns):
        return {}
    return {str(row["metric_name"]): str(row["metric_value"]) for _, row in frame.iterrows()}


def render_link_table(frame: pd.DataFrame, *, link_columns: dict[str, str] | None = None) -> None:
    link_columns = link_columns or {}
    column_config: dict[str, object] = {}
    for column_name, label in link_columns.items():
        if column_name in frame.columns:
            column_config[column_name] = st.column_config.LinkColumn(label)
    st.dataframe(frame, use_container_width=True, hide_index=True, column_config=column_config)


def reset_form(keys: list[str]) -> None:
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def apply_company_labels(frame: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["entity_key"] = output.apply(lambda row: entity_key(row["entity_type"], row["entity_name"]), axis=1)

    if labels.empty:
        output["classification"] = "未設定"
        output["review_status"] = "未設定"
        output["memo"] = ""
    else:
        labels = labels.copy()
        labels["entity_key"] = labels.apply(lambda row: entity_key(row["entity_type"], row["entity_name"]), axis=1)
        output = output.merge(
            labels[["entity_key", "classification", "review_status", "memo"]],
            how="left",
            on="entity_key",
        )
        output["classification"] = output["classification"].fillna("未設定")
        output["review_status"] = output["review_status"].fillna("未設定")
        output["memo"] = output["memo"].fillna("")

    output["classification"] = output["classification"].apply(normalize_manual_category)
    output["review_status"] = output["review_status"].apply(normalize_review_status)
    return output


def build_distributor_metadata(distributors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    frame = distributors.copy()
    frame["did"] = frame["did"].astype(str)
    frame["entity_type"] = "distributor"
    frame["entity_name"] = frame["distributor_name"]
    if "source_category" not in frame.columns:
        frame["source_category"] = "代理店・取扱店"
    frame = apply_company_labels(frame, labels)
    frame["display_category"] = frame.apply(
        lambda row: row["classification"]
        if row["classification"] != "未設定"
        else default_category_from_source(row.get("source_category", "")),
        axis=1,
    )
    return frame


def build_manufacturer_metadata(manufacturers: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    frame = manufacturers.copy()
    frame["entity_type"] = "manufacturer"
    frame["entity_name"] = frame["manufacturer_name"]
    frame["company_url"] = ""
    frame["location_url"] = ""
    frame["online_sales_url"] = ""
    frame["handling_makers_url"] = ""
    frame["manufacturer_page_url"] = frame["distributor_list_url"]
    frame = apply_company_labels(frame, labels)
    return frame


def build_company_index(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])

    manufacturer_rows = pd.DataFrame(
        {
            "entity_type": "manufacturer",
            "entity_name": manufacturers["manufacturer_name"],
            "company_type": "メーカー",
            "manufacturer_name": manufacturers["manufacturer_name"],
            "distributor_name": "",
            "relation_category": "メーカー",
            "classification": manufacturers["classification"],
            "review_status": manufacturers["review_status"],
            "memo": manufacturers["memo"],
            "initial": manufacturers["initial"],
            "company_url": manufacturers["company_url"],
            "location_url": manufacturers["location_url"],
            "online_sales_url": manufacturers["online_sales_url"],
            "handling_makers_url": manufacturers["handling_makers_url"],
            "manufacturer_page_url": manufacturers["manufacturer_page_url"],
        }
    )

    distributor_rows = pd.DataFrame(
        {
            "entity_type": "distributor",
            "entity_name": distributors["distributor_name"],
            "company_type": distributors["display_category"].replace("未設定", "代理店・取扱店"),
            "manufacturer_name": "",
            "distributor_name": distributors["distributor_name"],
            "relation_category": distributors["display_category"],
            "classification": distributors["classification"],
            "review_status": distributors["review_status"],
            "memo": distributors["memo"],
            "initial": distributors["initial"],
            "company_url": distributors["company_url"],
            "location_url": distributors["location_url"],
            "online_sales_url": distributors["online_sales_url"],
            "handling_makers_url": distributors["handling_makers_url"],
            "manufacturer_page_url": "",
        }
    )

    combined = pd.concat([manufacturer_rows, distributor_rows], ignore_index=True)
    return combined.drop_duplicates(subset=["entity_type", "entity_name"]).sort_values(["entity_name", "company_type"])


def build_unified_export(
    frame: pd.DataFrame,
    *,
    search_type: str,
    search_query: str,
) -> pd.DataFrame:
    export = frame.copy()
    export["search_type"] = search_type
    export["search_query"] = search_query
    return export.reindex(columns=UNIFIED_EXPORT_COLUMNS, fill_value="")


def render_unified_download(frame: pd.DataFrame, *, file_name: str) -> None:
    if frame.empty:
        return
    csv_bytes = frame.to_csv(index=False).encode("utf-8-sig")
    st.download_button("この結果をCSVダウンロード", data=csv_bytes, file_name=file_name, mime="text/csv")


def render_company_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("企業を自由検索する")
    controls_col, button_col = st.columns([5, 1])
    with controls_col:
        query = st.text_input("企業名", placeholder="例: 日伝 / 東芝テック / アイニックス", key="company_query")
    with button_col:
        st.write("")
        if st.button("クリア", key="company_clear"):
            reset_form(COMPANY_STATE_KEYS)
            st.rerun()

    if not query:
        st.info("メーカー・代理店・取扱店・オンライン販売をまとめて検索できます。")
        return

    company_index = build_company_index(data)
    hits = company_index[company_index["entity_name"].str.contains(query, case=False, na=False)].copy()
    company_type_filter = st.selectbox(
        "種別で絞り込み",
        ["すべて", *COMPANY_TYPE_OPTIONS],
        key="company_type_filter",
    )
    if company_type_filter != "すべて":
        hits = hits[hits["company_type"] == company_type_filter].copy()

    st.write(f"企業候補: {len(hits)}件")
    display_frame = hits.rename(
        columns={
            "entity_name": "企業名",
            "company_type": "種別",
            "review_status": "ステータス",
            "memo": "メモ",
        }
    )
    render_link_table(
        display_frame[
            [
                "企業名",
                "initial",
                "種別",
                "ステータス",
                "メモ",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
                "manufacturer_page_url",
            ]
        ],
        link_columns={
            "company_url": "会社URL",
            "location_url": "営業拠点URL",
            "online_sales_url": "オンライン販売URL",
            "handling_makers_url": "取扱メーカーURL",
            "manufacturer_page_url": "indexPro メーカーページ",
        },
    )
    render_company_metadata_editor(hits, data["labels"])
    render_unified_download(
        build_unified_export(hits, search_type="企業検索", search_query=query),
        file_name="company_search_results.csv",
    )


def render_manufacturer_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("メーカーから代理店・取扱店を探す")
    controls_col, button_col = st.columns([5, 1])
    with controls_col:
        query = st.text_input("メーカー名", placeholder="例: オムロン / キーエンス / SMC", key="manufacturer_query")
    with button_col:
        st.write("")
        if st.button("クリア", key="manufacturer_clear"):
            reset_form(MANUFACTURER_STATE_KEYS)
            st.rerun()

    if not query:
        st.info("メーカー名を入力すると、候補と関連する代理店・取扱店を表示します。")
        return

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    relations = data["relations"].copy()
    manufacturer_hits = manufacturers[manufacturers["manufacturer_name"].str.contains(query, case=False, na=False)].copy()

    st.write(f"メーカー候補: {len(manufacturer_hits)}件")
    render_link_table(
        manufacturer_hits.rename(columns={"manufacturer_name": "メーカー名"})[
            ["メーカー名", "initial", "manufacturer_page_url", "review_status", "memo"]
        ],
        link_columns={"manufacturer_page_url": "indexPro メーカーページ"},
    )
    if manufacturer_hits.empty:
        return

    selected = st.selectbox("対象メーカーを選択", manufacturer_hits["manufacturer_name"].tolist(), key="manufacturer_selected")
    selected_row = manufacturer_hits[manufacturer_hits["manufacturer_name"] == selected].iloc[0]

    related = relations[relations["manufacturer_name"] == selected].copy() if not relations.empty else pd.DataFrame()
    if not related.empty:
        related["did"] = related["did"].astype(str)
        related = related.merge(
            distributors[
                [
                    "did",
                    "distributor_name",
                    "initial",
                    "company_url",
                    "location_url",
                    "online_sales_url",
                    "handling_makers_url",
                    "classification",
                    "review_status",
                    "memo",
                ]
            ],
            how="left",
            on=["did", "distributor_name"],
            suffixes=("_relation", ""),
        )
        for column_name in ["company_url", "location_url", "online_sales_url"]:
            relation_column = f"{column_name}_relation"
            if relation_column in related.columns:
                related[column_name] = related[relation_column].fillna(related.get(column_name, ""))

    distributor_query = st.text_input(
        "代理店・取扱店名で絞り込み",
        placeholder="例: 佐鳥電機 / 日本電計",
        key="manufacturer_distributor_filter",
    )
    category_filter = st.selectbox(
        "区分で絞り込み",
        ["すべて", *CATEGORY_FILTER_OPTIONS],
        key="manufacturer_category_filter",
    )
    if not related.empty and distributor_query:
        related = related[related["distributor_name"].str.contains(distributor_query, case=False, na=False)].copy()
    if not related.empty and category_filter != "すべて":
        related = related[related["relation_category"] == category_filter].copy()

    st.write(f"代理店・取扱店: {len(related)}件")
    if not related.empty:
        display_frame = related.rename(
            columns={
                "relation_category": "区分",
                "review_status": "ステータス",
                "memo": "メモ",
            }
        )
        render_link_table(
            display_frame[
                [
                    "distributor_name",
                    "initial",
                    "区分",
                    "ステータス",
                    "メモ",
                    "company_url",
                    "location_url",
                    "online_sales_url",
                    "handling_makers_url",
                ]
            ],
            link_columns={
                "company_url": "会社URL",
                "location_url": "営業拠点URL",
                "online_sales_url": "オンライン販売URL",
                "handling_makers_url": "取扱メーカーURL",
            },
        )

        export_frame = pd.DataFrame(
            {
                "entity_type": "distributor",
                "entity_name": related["distributor_name"],
                "company_type": "代理店・取扱店",
                "manufacturer_name": related["manufacturer_name"],
                "distributor_name": related["distributor_name"],
                "relation_category": related["relation_category"],
                "classification": related["classification"],
                "review_status": related["review_status"],
                "memo": related["memo"],
                "initial": related["initial"],
                "company_url": related["company_url"],
                "location_url": related["location_url"],
                "online_sales_url": related["online_sales_url"],
                "handling_makers_url": related["handling_makers_url"],
                "manufacturer_page_url": "",
            }
        )
        render_unified_download(
            build_unified_export(export_frame, search_type="メーカー検索", search_query=selected),
            file_name=f"manufacturer_{selected_row['mcid']}_results.csv",
        )


def render_distributor_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("代理店・取扱店から取扱メーカーを探す")
    controls_col, button_col = st.columns([5, 1])
    with controls_col:
        query = st.text_input(
            "代理店・取扱店名",
            placeholder="例: 佐鳥電機 / 日本電計 / チップワンストップ",
            key="distributor_query",
        )
    with button_col:
        st.write("")
        if st.button("クリア", key="distributor_clear"):
            reset_form(DISTRIBUTOR_STATE_KEYS)
            st.rerun()

    if not query:
        st.info("代理店・取扱店名を入力すると候補と取扱メーカーを表示します。")
        return

    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    distributor_hits = distributors[distributors["distributor_name"].str.contains(query, case=False, na=False)].copy()

    st.write(f"代理店・取扱店候補: {len(distributor_hits)}件")
    if not distributor_hits.empty:
        render_link_table(
            distributor_hits.rename(columns={"review_status": "ステータス", "memo": "メモ"})[
                [
                    "distributor_name",
                    "initial",
                    "ステータス",
                    "メモ",
                    "company_url",
                    "location_url",
                    "online_sales_url",
                    "handling_makers_url",
                ]
            ],
            link_columns={
                "company_url": "会社URL",
                "location_url": "営業拠点URL",
                "online_sales_url": "オンライン販売URL",
                "handling_makers_url": "取扱メーカーURL",
            },
        )
    if distributor_hits.empty:
        return

    selected = st.selectbox(
        "対象代理店・取扱店を選択",
        distributor_hits["distributor_name"].tolist(),
        key="distributor_selected",
    )
    selected_row = distributor_hits[distributor_hits["distributor_name"] == selected].iloc[0]
    did = str(selected_row["did"])

    handlings = data["handlings"].copy()
    relations = data["relations"].copy()
    related = handlings[handlings["did"].astype(str) == did].copy()
    related["did"] = related["did"].astype(str)
    related = related.sort_values("handling_manufacturer_name")

    manufacturers = data["manufacturers"].copy()
    related = related.merge(
        manufacturers[["manufacturer_name", "distributor_list_url"]],
        how="left",
        left_on="handling_manufacturer_name",
        right_on="manufacturer_name",
    )
    related = related.rename(columns={"distributor_list_url": "manufacturer_page_url"})

    if not relations.empty:
        relation_subset = relations[["did", "manufacturer_name", "relation_category"]].copy()
        relation_subset["did"] = relation_subset["did"].astype(str)
        related = related.merge(
            relation_subset,
            how="left",
            left_on=["did", "handling_manufacturer_name"],
            right_on=["did", "manufacturer_name"],
        )
    related["relation_category"] = related["relation_category"].fillna("未設定")

    relation_filter = st.selectbox(
        "取扱メーカーの区分で絞り込み",
        ["すべて", *CATEGORY_FILTER_OPTIONS],
        key="distributor_relation_filter",
    )
    if relation_filter != "すべて":
        related = related[related["relation_category"] == relation_filter].copy()

    counts = related["relation_category"].value_counts()
    col1, col2, col3 = st.columns(3)
    col1.metric("代理店件数", str(int(counts.get("代理店", 0))))
    col2.metric("取扱店件数", str(int(counts.get("取扱店", 0))))
    col3.metric("オンライン販売件数", str(int(counts.get("オンライン販売", 0))))

    st.write(f"取扱メーカー: {len(related)}件")
    display_frame = related.rename(columns={"relation_category": "区分"})
    render_link_table(
        display_frame[
            [
                column_name
                for column_name in ["handling_manufacturer_name", "区分", "manufacturer_page_url"]
                if column_name in display_frame.columns
            ]
        ],
        link_columns={"manufacturer_page_url": "indexPro メーカーページ"},
    )

    related["entity_type"] = "distributor"
    related["entity_name"] = selected_row["distributor_name"]
    related["company_type"] = "代理店・取扱店"
    related["classification"] = selected_row["classification"]
    related["review_status"] = selected_row["review_status"]
    related["memo"] = selected_row["memo"]
    related["initial"] = selected_row["initial"]
    related["company_url"] = selected_row["company_url"]
    related["location_url"] = selected_row["location_url"]
    related["online_sales_url"] = selected_row["online_sales_url"]
    related["handling_makers_url"] = selected_row["handling_makers_url"]
    related["manufacturer_name"] = related["handling_manufacturer_name"]
    related["distributor_name"] = selected_row["distributor_name"]

    render_unified_download(
        build_unified_export(related, search_type="代理店・取扱店検索", search_query=selected),
        file_name=f"distributor_{did}_results.csv",
    )


def build_company_option_labels(company_frame: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    unique_rows = company_frame[["entity_type", "entity_name", "company_type", "initial"]].drop_duplicates()
    labels_by_key: dict[str, str] = {}
    keys: list[str] = []
    for row in unique_rows.itertuples(index=False):
        key = entity_key(str(row.entity_type), str(row.entity_name))
        label = f"{row.entity_name} [{row.company_type}]"
        if pd.notna(row.initial) and str(row.initial).strip():
            label = f"{label} ({row.initial})"
        labels_by_key[key] = label
        keys.append(key)
    return keys, labels_by_key


def render_company_metadata_editor(company_frame: pd.DataFrame, labels: pd.DataFrame) -> None:
    if company_frame.empty:
        return

    with st.expander("区分・ステータス・メモを設定する"):
        keys, labels_by_key = build_company_option_labels(company_frame)
        selected_key = st.selectbox(
            "対象企業",
            keys,
            format_func=lambda key: labels_by_key.get(key, key),
            key="company_editor_target",
        )
        entity_type, entity_name = selected_key.split(":", 1)
        current = get_current_metadata(labels, entity_type, entity_name)
        selected_category = st.selectbox(
            "区分",
            MANUAL_CATEGORY_OPTIONS,
            index=MANUAL_CATEGORY_OPTIONS.index(current["classification"]),
            key="company_editor_category",
        )
        selected_status = st.selectbox(
            "ステータス",
            REVIEW_STATUS_OPTIONS,
            index=REVIEW_STATUS_OPTIONS.index(current["review_status"]),
            key="company_editor_status",
        )
        memo_value = st.text_area(
            "メモ",
            value=current["memo"],
            height=100,
            key="company_editor_memo",
        )
        if st.button("保存", key="company_editor_save"):
            updated = upsert_metadata(labels, entity_type, entity_name, selected_category, selected_status, memo_value)
            save_labels(updated)
            st.success("設定を保存しました。")
            st.rerun()


def get_current_metadata(labels: pd.DataFrame, entity_type: str, entity_name: str) -> dict[str, str]:
    if labels.empty:
        return {"classification": "未設定", "review_status": "未設定", "memo": ""}
    matched = labels[
        (labels["entity_type"].astype(str) == str(entity_type))
        & (labels["entity_name"].astype(str) == str(entity_name))
    ]
    if matched.empty:
        return {"classification": "未設定", "review_status": "未設定", "memo": ""}
    row = matched.iloc[-1]
    return {
        "classification": normalize_manual_category(row.get("classification", "未設定")),
        "review_status": normalize_review_status(row.get("review_status", "未設定")),
        "memo": str(row.get("memo", "") or ""),
    }


def upsert_metadata(
    labels: pd.DataFrame,
    entity_type: str,
    entity_name: str,
    classification: str,
    review_status: str,
    memo: str,
) -> pd.DataFrame:
    updated = labels.copy()
    if not updated.empty:
        updated = updated[
            ~(
                (updated["entity_type"].astype(str) == str(entity_type))
                & (updated["entity_name"].astype(str) == str(entity_name))
            )
        ]
    new_row = pd.DataFrame(
        [
            {
                "entity_type": str(entity_type),
                "entity_name": str(entity_name),
                "classification": normalize_manual_category(classification),
                "review_status": normalize_review_status(review_status),
                "memo": str(memo or ""),
                "updated_at": pd.Timestamp.now().isoformat(),
            }
        ]
    )
    if updated.empty:
        return new_row
    return pd.concat([updated, new_row], ignore_index=True)


def _legacy_render_candidate_agent_lookup_text_input(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("メーカー × 取扱店から推定代理店を探す")

    input_col1, input_col2, button_col = st.columns([3, 3, 1])
    with input_col1:
        manufacturer_query = st.text_input(
            "メーカー名",
            placeholder="例: オムロン / 東芝テック / SMC",
            key="inference_manufacturer_query",
        )
    with input_col2:
        retailer_query = st.text_input(
            "取扱店名",
            placeholder="例: アイニックス / 日伝 / 今永電機産業",
            key="inference_retailer_query",
        )
    with button_col:
        st.write("")
        if st.button("クリア", key="inference_clear"):
            reset_form(INFERENCE_STATE_KEYS)
            st.rerun()

    manufacturer_query = manufacturer_query.strip()
    retailer_query = retailer_query.strip()
    search_clicked = st.button("検索", key="inference_search")

    if not manufacturer_query and not retailer_query:
        st.info("メーカー名と取扱店名を入力すると、両方に関係しそうな代理店候補を表示します。")
        return

    if not manufacturer_query or not retailer_query:
        st.info("メーカー名と取扱店名の両方を入力してください。")
        return

    if not search_clicked:
        st.caption("検索ボタンを押すと、取扱店側の関連メーカーとメーカー直下の代理店を突き合わせて候補を出します。")
        return

    results = get_candidate_agents_by_manufacturer_and_retailer(
        manufacturer_query,
        retailer_query,
        data["relations"],
        data["handlings"],
    )

    if not results:
        st.warning("推定代理店候補は0件でした。条件を変えて再度確認してください。")
        return

    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    result_frame = pd.DataFrame(
        [
            {
                "順位": item.rank,
                "代理店名": item.agent_name,
                "基本スコア": f"{item.score:.2f}",
                "score_value": item.score,
                "メーカーとの直接接続有無": "true" if item.has_direct_connection else "false",
                "取扱店側関連メーカー数": item.retailer_related_manufacturer_count,
                "関連メーカー件数": item.matched_related_manufacturer_count,
                "代理店総取扱メーカー数": item.agent_total_handling_count,
                "関連メーカー一覧": ", ".join(item.evidence_manufacturers),
            }
            for item in results
        ]
    )
    result_frame = result_frame.merge(
        distributors[
            [
                "distributor_name",
                "classification",
                "review_status",
                "memo",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        ].drop_duplicates(subset=["distributor_name"]),
        how="left",
        left_on="代理店名",
        right_on="distributor_name",
    )
    result_frame["classification"] = result_frame["classification"].fillna("")
    result_frame["review_status"] = result_frame["review_status"].fillna("")
    result_frame["memo"] = result_frame["memo"].fillna("")

    st.write(f"推定代理店候補: {len(result_frame)}件")
    render_link_table(
        result_frame[
            [
                "順位",
                "代理店名",
                "基本スコア",
                "メーカーとの直接接続有無",
                "取扱店側関連メーカー数",
                "関連メーカー件数",
                "代理店総取扱メーカー数",
                "関連メーカー一覧",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        ],
        link_columns={
            "company_url": "会社URL",
            "location_url": "営業拠点URL",
            "online_sales_url": "オンライン販売URL",
            "handling_makers_url": "取扱メーカーURL",
        },
    )

    export_frame = result_frame[
        [
            "順位",
            "代理店名",
            "基本スコア",
            "メーカーとの直接接続有無",
            "取扱店側関連メーカー数",
            "関連メーカー件数",
            "代理店総取扱メーカー数",
            "関連メーカー一覧",
            "classification",
            "review_status",
            "memo",
            "company_url",
            "location_url",
            "online_sales_url",
            "handling_makers_url",
        ]
    ].rename(
        columns={
            "classification": "区分",
            "review_status": "ステータス",
            "memo": "メモ",
            "company_url": "会社URL",
            "location_url": "営業拠点URL",
            "online_sales_url": "オンライン販売URL",
            "handling_makers_url": "取扱メーカーURL",
        }
    )
    render_unified_download(export_frame, file_name="candidate_agents_results.csv")


def main() -> None:
    st.set_page_config(
        page_title="indexPro 仕入先検索",
        page_icon=":material/account_tree:",
        layout="wide",
    )

    st.title("indexPro 仕入先検索")
    st.caption("企業検索、メーカー検索、代理店・取扱店検索、推定代理店検索を1つの画面で確認できます。")

    missing = find_missing_files()
    if missing:
        st.error("必要なCSVが見つかりません。先に一覧取得を実行してください。")
        for path in missing:
            st.code(str(path))
        st.stop()

    data = load_app_data()
    render_summary(data)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["企業検索", "メーカー検索", "代理店・取扱店検索", "推定代理店検索"]
    )
    with tab1:
        render_company_lookup(data)
    with tab2:
        render_manufacturer_lookup(data)
    with tab3:
        render_distributor_lookup(data)
    with tab4:
        render_candidate_agent_lookup(data)

def render_competitor_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("メーカーから推定競合メーカーを探す")

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    manufacturer_options = [""] + sorted(
        manufacturers["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist()
    )

    input_col1, input_col2, input_col3, button_col = st.columns([3, 2, 2, 1])
    with input_col1:
        manufacturer_query = st.selectbox(
            "メーカー名",
            manufacturer_options,
            index=0,
            key="competitor_manufacturer_query",
            format_func=lambda value: value or "選択してください",
        )
    with input_col2:
        exclude_large = st.checkbox(
            "取扱メーカー数が多すぎる代理店を除外",
            value=True,
            key="competitor_max_handling_enabled",
        )
    with input_col3:
        max_handling_count = st.number_input(
            "除外上限",
            min_value=1,
            value=30,
            step=1,
            key="competitor_max_handling_count",
            disabled=not exclude_large,
        )
    with button_col:
        st.write("")
        if st.button("クリア", key="competitor_clear"):
            reset_form(COMPETITOR_STATE_KEYS)
            st.rerun()

    manufacturer_query = str(manufacturer_query).strip()
    search_clicked = st.button("推定競合を検索", key="competitor_search")

    if not manufacturer_query:
        st.info("メーカー名を選択すると、共通代理店ベースの推定競合メーカー一覧を表示します。")
        return

    if not search_clicked:
        st.caption("検索ボタンを押すと、選択メーカーと同じ代理店で扱われている他メーカーをスコア化して並べます。")
        return

    results = get_competitor_candidates(
        manufacturer_query,
        data["relations"],
        data["handlings"],
        max_handling_count=int(max_handling_count) if exclude_large else None,
    )

    if not results:
        st.warning("推定競合メーカーは0件でした。除外条件を緩めるか、別のメーカーで確認してください。")
        return

    result_frame = pd.DataFrame(
        [
            {
                "順位": item.rank,
                "候補メーカー名": item.candidate_manufacturer_name,
                "共通代理店数": item.common_distributor_count,
                "選択メーカー代理店数": item.base_manufacturer_distributor_count,
                "候補メーカー代理店数": item.candidate_manufacturer_distributor_count,
                "基本スコア": f"{item.basic_score:.2f}",
                "類似度スコア": f"{item.similarity_score:.2f}",
                "共通代理店一覧": ", ".join(item.common_distributors),
            }
            for item in results[:50]
        ]
    )

    candidate_filter = st.text_input(
        "候補メーカー名で絞り込み",
        placeholder="例: オムロン / 三菱 / SMC",
        key="competitor_candidate_filter",
    ).strip()
    if candidate_filter:
        result_frame = result_frame[
            result_frame["候補メーカー名"].str.contains(candidate_filter, case=False, na=False)
        ].copy()

    st.write(f"推定競合メーカー: {len(result_frame)}件")
    render_link_table(
        result_frame[
            [
                "順位",
                "候補メーカー名",
                "共通代理店数",
                "選択メーカー代理店数",
                "候補メーカー代理店数",
                "基本スコア",
                "類似度スコア",
                "共通代理店一覧",
            ]
        ]
    )
    render_unified_download(result_frame, file_name="competitor_candidates_results.csv")


def main() -> None:
    st.set_page_config(
        page_title="indexPro 仕入先検索",
        page_icon=":material/account_tree:",
        layout="wide",
    )

    st.title("indexPro 仕入先検索")
    st.caption("企業検索、メーカー検索、代理店・取扱店検索、推定代理店検索、推定競合検索を1つの画面で確認できます。")

    missing = find_missing_files()
    if missing:
        st.error("必要なCSVが見つかりません。先に一覧取得を実行してください。")
        for path in missing:
            st.code(str(path))
        st.stop()

    data = load_app_data()
    render_summary(data)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["企業検索", "メーカー検索", "代理店・取扱店検索", "推定代理店検索", "推定競合検索"]
    )
    with tab1:
        render_company_lookup(data)
    with tab2:
        render_manufacturer_lookup(data)
    with tab3:
        render_distributor_lookup(data)
    with tab4:
        render_candidate_agent_lookup(data)
    with tab5:
        render_competitor_lookup(data)
    render_footer(data)


def render_competitor_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("メーカーから推定競合メーカーを探す")

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    manufacturer_options = [""] + sorted(
        manufacturers["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist()
    )

    input_col1, input_col2, input_col3, button_col = st.columns([3, 2, 2, 1])
    with input_col1:
        manufacturer_query = st.selectbox(
            "メーカー名",
            manufacturer_options,
            index=0,
            key="competitor_manufacturer_query",
            format_func=lambda value: value or "選択してください",
        )
    with input_col2:
        exclude_large = st.checkbox(
            "取扱メーカー数が多すぎる代理店を除外",
            value=True,
            key="competitor_max_handling_enabled",
        )
    with input_col3:
        max_handling_count = st.number_input(
            "除外上限",
            min_value=1,
            value=30,
            step=1,
            key="competitor_max_handling_count",
            disabled=not exclude_large,
        )
    with button_col:
        st.write("")
        if st.button("クリア", key="competitor_clear"):
            reset_form(COMPETITOR_STATE_KEYS)
            st.rerun()

    manufacturer_query = str(manufacturer_query).strip()
    search_clicked = st.button("推定競合を検索", key="competitor_search")

    if not manufacturer_query:
        st.info("メーカー名を選択すると、共通代理店ベースの推定競合メーカー一覧を表示します。")
        return

    if not search_clicked:
        st.caption("検索ボタンを押すと、選択メーカーと同じ代理店で扱われている他メーカーをスコア化して並べます。")
        return

    results = get_competitor_candidates(
        manufacturer_query,
        data["relations"],
        data["handlings"],
        max_handling_count=int(max_handling_count) if exclude_large else None,
    )

    if not results:
        st.warning("推定競合メーカーは0件でした。除外条件を緩めるか、別のメーカーで確認してください。")
        return

    result_frame = pd.DataFrame(
        [
            {
                "順位": item.rank,
                "候補メーカー名": item.candidate_manufacturer_name,
                "共通代理店数": item.common_distributor_count,
                "選択メーカー代理店数": item.base_manufacturer_distributor_count,
                "候補メーカー代理店数": item.candidate_manufacturer_distributor_count,
                "基本スコア": f"{item.basic_score:.2f}",
                "類似度スコア": f"{item.similarity_score:.2f}",
                "共通代理店一覧": ", ".join(item.common_distributors),
            }
            for item in results[:50]
        ]
    )
    result_frame = result_frame.merge(
        manufacturers[["manufacturer_name", "manufacturer_page_url"]].drop_duplicates(subset=["manufacturer_name"]),
        how="left",
        left_on="候補メーカー名",
        right_on="manufacturer_name",
    )

    candidate_filter = st.text_input(
        "候補メーカー名で絞り込み",
        placeholder="例: オムロン / 三菱 / SMC",
        key="competitor_candidate_filter",
    ).strip()
    if candidate_filter:
        result_frame = result_frame[
            result_frame["候補メーカー名"].str.contains(candidate_filter, case=False, na=False)
        ].copy()

    st.write(f"推定競合メーカー: {len(result_frame)}件")
    render_link_table(
        result_frame[
            [
                "順位",
                "候補メーカー名",
                "共通代理店数",
                "選択メーカー代理店数",
                "候補メーカー代理店数",
                "基本スコア",
                "類似度スコア",
                "manufacturer_page_url",
                "共通代理店一覧",
            ]
        ],
        link_columns={"manufacturer_page_url": "indexPro メーカーページ"},
    )
    render_unified_download(result_frame, file_name="competitor_candidates_results.csv")


def render_summary(data: dict[str, pd.DataFrame]) -> None:
    metrics = metrics_to_map(data["metrics"])
    validation = metrics_to_map(data["validation"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("メーカー数", metrics.get("manufacturer_count", "-"))
    col2.metric("代理店数", metrics.get("distributor_count", "-"))
    col3.metric("取扱関係数", metrics.get("handling_relation_count", "-"))
    col4.metric("未一致件数", validation.get("handling_unmatched", "-"))


def format_generated_date(value: str) -> str:
    text = str(value or "").strip()
    if "T" in text:
        return text.split("T", 1)[0]
    if " " in text:
        return text.split(" ", 1)[0]
    return text


def render_footer(data: dict[str, pd.DataFrame]) -> None:
    st.divider()
    metrics = metrics_to_map(data["metrics"])
    generated_date = format_generated_date(metrics.get("generated_at", ""))
    suffix = f" 最終更新日: {generated_date}" if generated_date else ""
    st.caption(
        "Copyright (c) 2026 Tomoki Hotei. "
        "社内利用向け試作版。公開情報を元に作成しており、内容の正確性・完全性を保証するものではありません。"
        + suffix
    )


if __name__ == "__main__":
    main()
