from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError

import pandas as pd
import streamlit as st

try:
    from .agent_inference import get_candidate_agents_by_manufacturer_and_retailer
    from .competitor_inference import get_competitor_candidates
    from .settings import (
        BASE_DIR,
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
        BASE_DIR,
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
DEPLOY_TRIGGER_FILE = BASE_DIR / "deploy_trigger.txt"
LOGIN_ID = "MTB2026"
LOGIN_STATE_KEY = "app_authenticated"
LOGIN_INPUT_KEY = "login_id_input"

CATEGORY_FILTER_OPTIONS = ["莉｣逅・ｺ・, "蜿匁桶蠎・, "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ"]
MANUAL_CATEGORY_OPTIONS = ["譛ｪ險ｭ螳・, *CATEGORY_FILTER_OPTIONS]
REVIEW_STATUS_OPTIONS = ["譛ｪ險ｭ螳・, "隕∫｢ｺ隱・, "譛牙鴨蛟呵｣・, "譌｢蟄伜叙蠑輔≠繧・]
COMPANY_TYPE_OPTIONS = ["繝｡繝ｼ繧ｫ繝ｼ", "莉｣逅・ｺ・, "蜿匁桶蠎・, "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ"]

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
        frame["classification"] = "譛ｪ險ｭ螳・
    if "review_status" not in frame.columns:
        frame["review_status"] = "譛ｪ險ｭ螳・
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
    if text in {"莉｣逅・ｺ励・蜿匁桶蠎・, "莉｣逅・ｺ・}:
        return "莉｣逅・ｺ・
    if text == "蜿匁桶蠎・:
        return "蜿匁桶蠎・
    if text in {"繧ｪ繝ｳ繝ｩ繧､繝ｳ", "Web", "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ"}:
        return "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ"
    return "譛ｪ險ｭ螳・


def normalize_review_status(value: object) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text in REVIEW_STATUS_OPTIONS else "譛ｪ險ｭ螳・


def default_category_from_source(source_category: object) -> str:
    return "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ" if str(source_category).strip() == "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ" else "譛ｪ險ｭ螳・


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


def require_login() -> None:
    if st.session_state.get(LOGIN_STATE_KEY):
        return

    st.title("indexPro 莉募・蜈域､懃ｴ｢")
    st.subheader("繝ｭ繧ｰ繧､繝ｳ")
    st.caption("繧｢繝励Μ繧帝幕縺上↓縺ｯ繝ｭ繧ｰ繧､繝ｳID繧貞・蜉帙＠縺ｦ縺上□縺輔＞縲・)

    with st.form("login_form", clear_on_submit=False):
        login_id = st.text_input("繝ｭ繧ｰ繧､繝ｳID", key=LOGIN_INPUT_KEY)
        submitted = st.form_submit_button("繝ｭ繧ｰ繧､繝ｳ")

    if submitted:
        if login_id.strip() == LOGIN_ID:
            st.session_state[LOGIN_STATE_KEY] = True
            st.rerun()
        else:
            st.error("繝ｭ繧ｰ繧､繝ｳID縺御ｸ閾ｴ縺励∪縺帙ｓ縲・)

    st.stop()


def render_candidate_agent_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("繝｡繝ｼ繧ｫ繝ｼ ﾃ・蜿匁桶蠎励°繧画耳螳壻ｻ｣逅・ｺ励ｒ謗｢縺・)

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    manufacturer_options = [""] + sorted(
        manufacturers["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist()
    )

    relations = data["relations"].copy()
    retailer_options = [""]
    if not relations.empty:
        retailer_options += sorted(
            relations.loc[
                relations["relation_category"].astype(str) == "蜿匁桶蠎・,
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
            "繝｡繝ｼ繧ｫ繝ｼ蜷・,
            manufacturer_options,
            index=0,
            key="inference_manufacturer_query",
            format_func=lambda value: value or "驕ｸ謚槭＠縺ｦ縺上□縺輔＞",
        )
    with input_col2:
        retailer_query = st.selectbox(
            "蜿匁桶蠎怜錐",
            retailer_options,
            index=0,
            key="inference_retailer_query",
            format_func=lambda value: value or "驕ｸ謚槭＠縺ｦ縺上□縺輔＞",
        )
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="inference_clear"):
            reset_form(INFERENCE_STATE_KEYS)
            st.rerun()

    manufacturer_query = str(manufacturer_query).strip()
    retailer_query = str(retailer_query).strip()
    search_clicked = st.button("讀懃ｴ｢", key="inference_search")

    if not manufacturer_query and not retailer_query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪→蜿匁桶蠎怜錐繧帝∈謚槭☆繧九→縲∽ｸ｡譁ｹ縺ｫ髢｢菫ゅ＠縺昴≧縺ｪ莉｣逅・ｺ怜呵｣懊ｒ陦ｨ遉ｺ縺励∪縺吶・)
        return

    if not manufacturer_query or not retailer_query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪→蜿匁桶蠎怜錐縺ｮ荳｡譁ｹ繧帝∈謚槭＠縺ｦ縺上□縺輔＞縲・)
        return

    if not search_clicked:
        st.caption("讀懃ｴ｢繝懊ち繝ｳ繧呈款縺吶→縲∝叙謇ｱ蠎怜・縺ｮ髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ縺ｨ繝｡繝ｼ繧ｫ繝ｼ逶ｴ荳九・莉｣逅・ｺ励ｒ遯√″蜷医ｏ縺帙※蛟呵｣懊ｒ蜃ｺ縺励∪縺吶・)
        return

    results = get_candidate_agents_by_manufacturer_and_retailer(
        manufacturer_query,
        retailer_query,
        data["relations"],
        data["handlings"],
    )

    if not results:
        st.warning("謗ｨ螳壻ｻ｣逅・ｺ怜呵｣懊・0莉ｶ縺ｧ縺励◆縲よ擅莉ｶ繧貞､峨∴縺ｦ蜀榊ｺｦ遒ｺ隱阪＠縺ｦ縺上□縺輔＞縲・)
        return

    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    result_frame = pd.DataFrame(
        [
            {
                "鬆・ｽ・: item.rank,
                "莉｣逅・ｺ怜錐": item.agent_name,
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢": f"{item.score:.2f}",
                "score_value": item.score,
                "繝｡繝ｼ繧ｫ繝ｼ縺ｨ縺ｮ逶ｴ謗･謗･邯壽怏辟｡": "true" if item.has_direct_connection else "false",
                "蜿匁桶蠎怜・髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ謨ｰ": item.retailer_related_manufacturer_count,
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ莉ｶ謨ｰ": item.matched_related_manufacturer_count,
                "莉｣逅・ｺ礼ｷ丞叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ謨ｰ": item.agent_total_handling_count,
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ荳隕ｧ": ", ".join(item.evidence_manufacturers),
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
        left_on="莉｣逅・ｺ怜錐",
        right_on="distributor_name",
    )
    result_frame["classification"] = result_frame["classification"].fillna("")
    result_frame["review_status"] = result_frame["review_status"].fillna("")
    result_frame["memo"] = result_frame["memo"].fillna("")

    st.write(f"謗ｨ螳壻ｻ｣逅・ｺ怜呵｣・ {len(result_frame)}莉ｶ")
    render_link_table(
        result_frame[
            [
                "鬆・ｽ・,
                "莉｣逅・ｺ怜錐",
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢",
                "繝｡繝ｼ繧ｫ繝ｼ縺ｨ縺ｮ逶ｴ謗･謗･邯壽怏辟｡",
                "蜿匁桶蠎怜・髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ莉ｶ謨ｰ",
                "莉｣逅・ｺ礼ｷ丞叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ荳隕ｧ",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        ],
        link_columns={
            "company_url": "莨夂､ｾURL",
            "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
            "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
            "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
        },
    )

    export_frame = result_frame[
        [
            "鬆・ｽ・,
            "莉｣逅・ｺ怜錐",
            "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢",
            "繝｡繝ｼ繧ｫ繝ｼ縺ｨ縺ｮ逶ｴ謗･謗･邯壽怏辟｡",
            "蜿匁桶蠎怜・髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
            "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ莉ｶ謨ｰ",
            "莉｣逅・ｺ礼ｷ丞叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
            "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ荳隕ｧ",
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
            "classification": "蛹ｺ蛻・,
            "review_status": "繧ｹ繝・・繧ｿ繧ｹ",
            "memo": "繝｡繝｢",
            "company_url": "莨夂､ｾURL",
            "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
            "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
            "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
        }
    )
    render_unified_download(export_frame, file_name="candidate_agents_results.csv")


def main() -> None:
    st.set_page_config(
        page_title="indexPro 莉募・蜈域､懃ｴ｢",
        page_icon=":material/account_tree:",
        layout="wide",
    )

    st.title("indexPro 莉募・蜈域､懃ｴ｢")
    st.caption("莨∵･ｭ讀懃ｴ｢縲√Γ繝ｼ繧ｫ繝ｼ讀懃ｴ｢縲∽ｻ｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢繧・縺､縺ｮ逕ｻ髱｢縺ｧ遒ｺ隱阪〒縺阪∪縺吶・)

    require_login()

    require_login()

    require_login()

    require_login()

    require_login()
    missing = find_missing_files()
    if missing:
        st.error("蠢・ｦ√↑CSV縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲ょ・縺ｫ荳隕ｧ蜿朱寔繧貞ｮ溯｡後＠縺ｦ縺上□縺輔＞縲・)
        for path in missing:
            st.code(str(path))
        st.stop()

    data = load_app_data()
    render_summary(data)

    tab1, tab2, tab3 = st.tabs(["莨∵･ｭ讀懃ｴ｢", "繝｡繝ｼ繧ｫ繝ｼ讀懃ｴ｢", "莉｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢"])
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
    col1.metric("繝｡繝ｼ繧ｫ繝ｼ謨ｰ", metrics.get("manufacturer_count", "-"))
    col2.metric("莉｣逅・ｺ玲焚", metrics.get("distributor_count", "-"))
    col3.metric("蜿匁桶髢｢菫よ焚", metrics.get("handling_relation_count", "-"))
    col4.metric("譛ｪ荳閾ｴ莉ｶ謨ｰ", validation.get("handling_unmatched", "-"))


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
        output["classification"] = "譛ｪ險ｭ螳・
        output["review_status"] = "譛ｪ險ｭ螳・
        output["memo"] = ""
    else:
        labels = labels.copy()
        labels["entity_key"] = labels.apply(lambda row: entity_key(row["entity_type"], row["entity_name"]), axis=1)
        output = output.merge(
            labels[["entity_key", "classification", "review_status", "memo"]],
            how="left",
            on="entity_key",
        )
        output["classification"] = output["classification"].fillna("譛ｪ險ｭ螳・)
        output["review_status"] = output["review_status"].fillna("譛ｪ險ｭ螳・)
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
        frame["source_category"] = "莉｣逅・ｺ励・蜿匁桶蠎・
    frame = apply_company_labels(frame, labels)
    frame["display_category"] = frame.apply(
        lambda row: row["classification"]
        if row["classification"] != "譛ｪ險ｭ螳・
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
            "company_type": "繝｡繝ｼ繧ｫ繝ｼ",
            "manufacturer_name": manufacturers["manufacturer_name"],
            "distributor_name": "",
            "relation_category": "繝｡繝ｼ繧ｫ繝ｼ",
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
            "company_type": distributors["display_category"].replace("譛ｪ險ｭ螳・, "莉｣逅・ｺ励・蜿匁桶蠎・),
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
    st.download_button("縺薙・邨先棡繧辰SV繝繧ｦ繝ｳ繝ｭ繝ｼ繝・, data=csv_bytes, file_name=file_name, mime="text/csv")


def render_company_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("莨∵･ｭ繧定・逕ｱ讀懃ｴ｢縺吶ｋ")
    controls_col, button_col = st.columns([5, 1])
    with controls_col:
        query = st.text_input("莨∵･ｭ蜷・, placeholder="萓・ 譌･莨・/ 譚ｱ闃昴ユ繝・け / 繧｢繧､繝九ャ繧ｯ繧ｹ", key="company_query")
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="company_clear"):
            reset_form(COMPANY_STATE_KEYS)
            st.rerun()

    if not query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ繝ｻ莉｣逅・ｺ励・蜿匁桶蠎励・繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ繧偵∪縺ｨ繧√※讀懃ｴ｢縺ｧ縺阪∪縺吶・)
        return

    company_index = build_company_index(data)
    hits = company_index[company_index["entity_name"].str.contains(query, case=False, na=False)].copy()
    company_type_filter = st.selectbox(
        "遞ｮ蛻･縺ｧ邨槭ｊ霎ｼ縺ｿ",
        ["縺吶∋縺ｦ", *COMPANY_TYPE_OPTIONS],
        key="company_type_filter",
    )
    if company_type_filter != "縺吶∋縺ｦ":
        hits = hits[hits["company_type"] == company_type_filter].copy()

    st.write(f"莨∵･ｭ蛟呵｣・ {len(hits)}莉ｶ")
    display_frame = hits.rename(
        columns={
            "entity_name": "莨∵･ｭ蜷・,
            "company_type": "遞ｮ蛻･",
            "review_status": "繧ｹ繝・・繧ｿ繧ｹ",
            "memo": "繝｡繝｢",
        }
    )
    render_link_table(
        display_frame[
            [
                "莨∵･ｭ蜷・,
                "initial",
                "遞ｮ蛻･",
                "繧ｹ繝・・繧ｿ繧ｹ",
                "繝｡繝｢",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
                "manufacturer_page_url",
            ]
        ],
        link_columns={
            "company_url": "莨夂､ｾURL",
            "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
            "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
            "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
            "manufacturer_page_url": "indexPro 繝｡繝ｼ繧ｫ繝ｼ繝壹・繧ｸ",
        },
    )
    render_company_metadata_editor(hits, data["labels"])
    render_unified_download(
        build_unified_export(hits, search_type="莨∵･ｭ讀懃ｴ｢", search_query=query),
        file_name="company_search_results.csv",
    )


def render_manufacturer_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("繝｡繝ｼ繧ｫ繝ｼ縺九ｉ莉｣逅・ｺ励・蜿匁桶蠎励ｒ謗｢縺・)
    controls_col, button_col = st.columns([5, 1])
    with controls_col:
        query = st.text_input("繝｡繝ｼ繧ｫ繝ｼ蜷・, placeholder="萓・ 繧ｪ繝繝ｭ繝ｳ / 繧ｭ繝ｼ繧ｨ繝ｳ繧ｹ / SMC", key="manufacturer_query")
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="manufacturer_clear"):
            reset_form(MANUFACTURER_STATE_KEYS)
            st.rerun()

    if not query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪ｒ蜈･蜉帙☆繧九→縲∝呵｣懊→髢｢騾｣縺吶ｋ莉｣逅・ｺ励・蜿匁桶蠎励ｒ陦ｨ遉ｺ縺励∪縺吶・)
        return

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    relations = data["relations"].copy()
    manufacturer_hits = manufacturers[manufacturers["manufacturer_name"].str.contains(query, case=False, na=False)].copy()

    st.write(f"繝｡繝ｼ繧ｫ繝ｼ蛟呵｣・ {len(manufacturer_hits)}莉ｶ")
    render_link_table(
        manufacturer_hits.rename(columns={"manufacturer_name": "繝｡繝ｼ繧ｫ繝ｼ蜷・})[
            ["繝｡繝ｼ繧ｫ繝ｼ蜷・, "initial", "manufacturer_page_url", "review_status", "memo"]
        ],
        link_columns={"manufacturer_page_url": "indexPro 繝｡繝ｼ繧ｫ繝ｼ繝壹・繧ｸ"},
    )
    if manufacturer_hits.empty:
        return

    selected = st.selectbox("蟇ｾ雎｡繝｡繝ｼ繧ｫ繝ｼ繧帝∈謚・, manufacturer_hits["manufacturer_name"].tolist(), key="manufacturer_selected")
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
        "莉｣逅・ｺ励・蜿匁桶蠎怜錐縺ｧ邨槭ｊ霎ｼ縺ｿ",
        placeholder="萓・ 菴宣ｳ･髮ｻ讖・/ 譌･譛ｬ髮ｻ險・,
        key="manufacturer_distributor_filter",
    )
    category_filter = st.selectbox(
        "蛹ｺ蛻・〒邨槭ｊ霎ｼ縺ｿ",
        ["縺吶∋縺ｦ", *CATEGORY_FILTER_OPTIONS],
        key="manufacturer_category_filter",
    )
    if not related.empty and distributor_query:
        related = related[related["distributor_name"].str.contains(distributor_query, case=False, na=False)].copy()
    if not related.empty and category_filter != "縺吶∋縺ｦ":
        related = related[related["relation_category"] == category_filter].copy()

    st.write(f"莉｣逅・ｺ励・蜿匁桶蠎・ {len(related)}莉ｶ")
    if not related.empty:
        display_frame = related.rename(
            columns={
                "relation_category": "蛹ｺ蛻・,
                "review_status": "繧ｹ繝・・繧ｿ繧ｹ",
                "memo": "繝｡繝｢",
            }
        )
        render_link_table(
            display_frame[
                [
                    "distributor_name",
                    "initial",
                    "蛹ｺ蛻・,
                    "繧ｹ繝・・繧ｿ繧ｹ",
                    "繝｡繝｢",
                    "company_url",
                    "location_url",
                    "online_sales_url",
                    "handling_makers_url",
                ]
            ],
            link_columns={
                "company_url": "莨夂､ｾURL",
                "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
                "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
                "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
            },
        )

        export_frame = pd.DataFrame(
            {
                "entity_type": "distributor",
                "entity_name": related["distributor_name"],
                "company_type": "莉｣逅・ｺ励・蜿匁桶蠎・,
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
            build_unified_export(export_frame, search_type="繝｡繝ｼ繧ｫ繝ｼ讀懃ｴ｢", search_query=selected),
            file_name=f"manufacturer_{selected_row['mcid']}_results.csv",
        )


def render_distributor_lookup(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("莉｣逅・ｺ励・蜿匁桶蠎励°繧牙叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ繧呈爾縺・)
    controls_col, button_col = st.columns([5, 1])
    with controls_col:
        query = st.text_input(
            "莉｣逅・ｺ励・蜿匁桶蠎怜錐",
            placeholder="萓・ 菴宣ｳ･髮ｻ讖・/ 譌･譛ｬ髮ｻ險・/ 繝√ャ繝励Ρ繝ｳ繧ｹ繝医ャ繝・,
            key="distributor_query",
        )
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="distributor_clear"):
            reset_form(DISTRIBUTOR_STATE_KEYS)
            st.rerun()

    if not query:
        st.info("莉｣逅・ｺ励・蜿匁桶蠎怜錐繧貞・蜉帙☆繧九→蛟呵｣懊→蜿匁桶繝｡繝ｼ繧ｫ繝ｼ繧定｡ｨ遉ｺ縺励∪縺吶・)
        return

    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    distributor_hits = distributors[distributors["distributor_name"].str.contains(query, case=False, na=False)].copy()

    st.write(f"莉｣逅・ｺ励・蜿匁桶蠎怜呵｣・ {len(distributor_hits)}莉ｶ")
    if not distributor_hits.empty:
        render_link_table(
            distributor_hits.rename(columns={"review_status": "繧ｹ繝・・繧ｿ繧ｹ", "memo": "繝｡繝｢"})[
                [
                    "distributor_name",
                    "initial",
                    "繧ｹ繝・・繧ｿ繧ｹ",
                    "繝｡繝｢",
                    "company_url",
                    "location_url",
                    "online_sales_url",
                    "handling_makers_url",
                ]
            ],
            link_columns={
                "company_url": "莨夂､ｾURL",
                "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
                "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
                "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
            },
        )
    if distributor_hits.empty:
        return

    selected = st.selectbox(
        "蟇ｾ雎｡莉｣逅・ｺ励・蜿匁桶蠎励ｒ驕ｸ謚・,
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
    related["relation_category"] = related["relation_category"].fillna("譛ｪ險ｭ螳・)

    relation_filter = st.selectbox(
        "蜿匁桶繝｡繝ｼ繧ｫ繝ｼ縺ｮ蛹ｺ蛻・〒邨槭ｊ霎ｼ縺ｿ",
        ["縺吶∋縺ｦ", *CATEGORY_FILTER_OPTIONS],
        key="distributor_relation_filter",
    )
    if relation_filter != "縺吶∋縺ｦ":
        related = related[related["relation_category"] == relation_filter].copy()

    counts = related["relation_category"].value_counts()
    col1, col2, col3 = st.columns(3)
    col1.metric("莉｣逅・ｺ嶺ｻｶ謨ｰ", str(int(counts.get("莉｣逅・ｺ・, 0))))
    col2.metric("蜿匁桶蠎嶺ｻｶ謨ｰ", str(int(counts.get("蜿匁桶蠎・, 0))))
    col3.metric("繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ莉ｶ謨ｰ", str(int(counts.get("繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲ", 0))))

    st.write(f"蜿匁桶繝｡繝ｼ繧ｫ繝ｼ: {len(related)}莉ｶ")
    display_frame = related.rename(columns={"relation_category": "蛹ｺ蛻・})
    render_link_table(
        display_frame[
            [
                column_name
                for column_name in ["handling_manufacturer_name", "蛹ｺ蛻・, "manufacturer_page_url"]
                if column_name in display_frame.columns
            ]
        ],
        link_columns={"manufacturer_page_url": "indexPro 繝｡繝ｼ繧ｫ繝ｼ繝壹・繧ｸ"},
    )

    related["entity_type"] = "distributor"
    related["entity_name"] = selected_row["distributor_name"]
    related["company_type"] = "莉｣逅・ｺ励・蜿匁桶蠎・
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
        build_unified_export(related, search_type="莉｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢", search_query=selected),
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

    with st.expander("蛹ｺ蛻・・繧ｹ繝・・繧ｿ繧ｹ繝ｻ繝｡繝｢繧定ｨｭ螳壹☆繧・):
        keys, labels_by_key = build_company_option_labels(company_frame)
        selected_key = st.selectbox(
            "蟇ｾ雎｡莨∵･ｭ",
            keys,
            format_func=lambda key: labels_by_key.get(key, key),
            key="company_editor_target",
        )
        entity_type, entity_name = selected_key.split(":", 1)
        current = get_current_metadata(labels, entity_type, entity_name)
        selected_category = st.selectbox(
            "蛹ｺ蛻・,
            MANUAL_CATEGORY_OPTIONS,
            index=MANUAL_CATEGORY_OPTIONS.index(current["classification"]),
            key="company_editor_category",
        )
        selected_status = st.selectbox(
            "繧ｹ繝・・繧ｿ繧ｹ",
            REVIEW_STATUS_OPTIONS,
            index=REVIEW_STATUS_OPTIONS.index(current["review_status"]),
            key="company_editor_status",
        )
        memo_value = st.text_area(
            "繝｡繝｢",
            value=current["memo"],
            height=100,
            key="company_editor_memo",
        )
        if st.button("菫晏ｭ・, key="company_editor_save"):
            updated = upsert_metadata(labels, entity_type, entity_name, selected_category, selected_status, memo_value)
            save_labels(updated)
            st.success("險ｭ螳壹ｒ菫晏ｭ倥＠縺ｾ縺励◆縲・)
            st.rerun()


def get_current_metadata(labels: pd.DataFrame, entity_type: str, entity_name: str) -> dict[str, str]:
    if labels.empty:
        return {"classification": "譛ｪ險ｭ螳・, "review_status": "譛ｪ險ｭ螳・, "memo": ""}
    matched = labels[
        (labels["entity_type"].astype(str) == str(entity_type))
        & (labels["entity_name"].astype(str) == str(entity_name))
    ]
    if matched.empty:
        return {"classification": "譛ｪ險ｭ螳・, "review_status": "譛ｪ險ｭ螳・, "memo": ""}
    row = matched.iloc[-1]
    return {
        "classification": normalize_manual_category(row.get("classification", "譛ｪ險ｭ螳・)),
        "review_status": normalize_review_status(row.get("review_status", "譛ｪ險ｭ螳・)),
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
    st.subheader("繝｡繝ｼ繧ｫ繝ｼ ﾃ・蜿匁桶蠎励°繧画耳螳壻ｻ｣逅・ｺ励ｒ謗｢縺・)

    input_col1, input_col2, button_col = st.columns([3, 3, 1])
    with input_col1:
        manufacturer_query = st.text_input(
            "繝｡繝ｼ繧ｫ繝ｼ蜷・,
            placeholder="萓・ 繧ｪ繝繝ｭ繝ｳ / 譚ｱ闃昴ユ繝・け / SMC",
            key="inference_manufacturer_query",
        )
    with input_col2:
        retailer_query = st.text_input(
            "蜿匁桶蠎怜錐",
            placeholder="萓・ 繧｢繧､繝九ャ繧ｯ繧ｹ / 譌･莨・/ 莉頑ｰｸ髮ｻ讖溽肇讌ｭ",
            key="inference_retailer_query",
        )
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="inference_clear"):
            reset_form(INFERENCE_STATE_KEYS)
            st.rerun()

    manufacturer_query = manufacturer_query.strip()
    retailer_query = retailer_query.strip()
    search_clicked = st.button("讀懃ｴ｢", key="inference_search")

    if not manufacturer_query and not retailer_query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪→蜿匁桶蠎怜錐繧貞・蜉帙☆繧九→縲∽ｸ｡譁ｹ縺ｫ髢｢菫ゅ＠縺昴≧縺ｪ莉｣逅・ｺ怜呵｣懊ｒ陦ｨ遉ｺ縺励∪縺吶・)
        return

    if not manufacturer_query or not retailer_query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪→蜿匁桶蠎怜錐縺ｮ荳｡譁ｹ繧貞・蜉帙＠縺ｦ縺上□縺輔＞縲・)
        return

    if not search_clicked:
        st.caption("讀懃ｴ｢繝懊ち繝ｳ繧呈款縺吶→縲∝叙謇ｱ蠎怜・縺ｮ髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ縺ｨ繝｡繝ｼ繧ｫ繝ｼ逶ｴ荳九・莉｣逅・ｺ励ｒ遯√″蜷医ｏ縺帙※蛟呵｣懊ｒ蜃ｺ縺励∪縺吶・)
        return

    results = get_candidate_agents_by_manufacturer_and_retailer(
        manufacturer_query,
        retailer_query,
        data["relations"],
        data["handlings"],
    )

    if not results:
        st.warning("謗ｨ螳壻ｻ｣逅・ｺ怜呵｣懊・0莉ｶ縺ｧ縺励◆縲よ擅莉ｶ繧貞､峨∴縺ｦ蜀榊ｺｦ遒ｺ隱阪＠縺ｦ縺上□縺輔＞縲・)
        return

    distributors = build_distributor_metadata(data["distributors"].copy(), data["labels"])
    result_frame = pd.DataFrame(
        [
            {
                "鬆・ｽ・: item.rank,
                "莉｣逅・ｺ怜錐": item.agent_name,
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢": f"{item.score:.2f}",
                "score_value": item.score,
                "繝｡繝ｼ繧ｫ繝ｼ縺ｨ縺ｮ逶ｴ謗･謗･邯壽怏辟｡": "true" if item.has_direct_connection else "false",
                "蜿匁桶蠎怜・髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ謨ｰ": item.retailer_related_manufacturer_count,
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ莉ｶ謨ｰ": item.matched_related_manufacturer_count,
                "莉｣逅・ｺ礼ｷ丞叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ謨ｰ": item.agent_total_handling_count,
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ荳隕ｧ": ", ".join(item.evidence_manufacturers),
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
        left_on="莉｣逅・ｺ怜錐",
        right_on="distributor_name",
    )
    result_frame["classification"] = result_frame["classification"].fillna("")
    result_frame["review_status"] = result_frame["review_status"].fillna("")
    result_frame["memo"] = result_frame["memo"].fillna("")

    st.write(f"謗ｨ螳壻ｻ｣逅・ｺ怜呵｣・ {len(result_frame)}莉ｶ")
    render_link_table(
        result_frame[
            [
                "鬆・ｽ・,
                "莉｣逅・ｺ怜錐",
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢",
                "繝｡繝ｼ繧ｫ繝ｼ縺ｨ縺ｮ逶ｴ謗･謗･邯壽怏辟｡",
                "蜿匁桶蠎怜・髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ莉ｶ謨ｰ",
                "莉｣逅・ｺ礼ｷ丞叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
                "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ荳隕ｧ",
                "company_url",
                "location_url",
                "online_sales_url",
                "handling_makers_url",
            ]
        ],
        link_columns={
            "company_url": "莨夂､ｾURL",
            "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
            "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
            "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
        },
    )

    export_frame = result_frame[
        [
            "鬆・ｽ・,
            "莉｣逅・ｺ怜錐",
            "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢",
            "繝｡繝ｼ繧ｫ繝ｼ縺ｨ縺ｮ逶ｴ謗･謗･邯壽怏辟｡",
            "蜿匁桶蠎怜・髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
            "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ莉ｶ謨ｰ",
            "莉｣逅・ｺ礼ｷ丞叙謇ｱ繝｡繝ｼ繧ｫ繝ｼ謨ｰ",
            "髢｢騾｣繝｡繝ｼ繧ｫ繝ｼ荳隕ｧ",
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
            "classification": "蛹ｺ蛻・,
            "review_status": "繧ｹ繝・・繧ｿ繧ｹ",
            "memo": "繝｡繝｢",
            "company_url": "莨夂､ｾURL",
            "location_url": "蝟ｶ讌ｭ諡轤ｹURL",
            "online_sales_url": "繧ｪ繝ｳ繝ｩ繧､繝ｳ雋ｩ螢ｲURL",
            "handling_makers_url": "蜿匁桶繝｡繝ｼ繧ｫ繝ｼURL",
        }
    )
    render_unified_download(export_frame, file_name="candidate_agents_results.csv")


def main() -> None:
    st.set_page_config(
        page_title="indexPro 莉募・蜈域､懃ｴ｢",
        page_icon=":material/account_tree:",
        layout="wide",
    )

    st.title("indexPro 莉募・蜈域､懃ｴ｢")
    st.caption("莨∵･ｭ讀懃ｴ｢縲√Γ繝ｼ繧ｫ繝ｼ讀懃ｴ｢縲∽ｻ｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢縲∵耳螳壻ｻ｣逅・ｺ玲､懃ｴ｢繧・縺､縺ｮ逕ｻ髱｢縺ｧ遒ｺ隱阪〒縺阪∪縺吶・)

    require_login()

    missing = find_missing_files()
    if missing:
        st.error("蠢・ｦ√↑CSV縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲ょ・縺ｫ荳隕ｧ蜿門ｾ励ｒ螳溯｡後＠縺ｦ縺上□縺輔＞縲・)
        for path in missing:
            st.code(str(path))
        st.stop()

    data = load_app_data()
    render_summary(data)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["莨∵･ｭ讀懃ｴ｢", "繝｡繝ｼ繧ｫ繝ｼ讀懃ｴ｢", "莉｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢", "謗ｨ螳壻ｻ｣逅・ｺ玲､懃ｴ｢"]
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
    st.subheader("繝｡繝ｼ繧ｫ繝ｼ縺九ｉ謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ繧呈爾縺・)

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    manufacturer_options = [""] + sorted(
        manufacturers["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist()
    )

    input_col1, input_col2, input_col3, button_col = st.columns([3, 2, 2, 1])
    with input_col1:
        manufacturer_query = st.selectbox(
            "繝｡繝ｼ繧ｫ繝ｼ蜷・,
            manufacturer_options,
            index=0,
            key="competitor_manufacturer_query",
            format_func=lambda value: value or "驕ｸ謚槭＠縺ｦ縺上□縺輔＞",
        )
    with input_col2:
        exclude_large = st.checkbox(
            "蜿匁桶繝｡繝ｼ繧ｫ繝ｼ謨ｰ縺悟､壹☆縺弱ｋ莉｣逅・ｺ励ｒ髯､螟・,
            value=True,
            key="competitor_max_handling_enabled",
        )
    with input_col3:
        max_handling_count = st.number_input(
            "髯､螟紋ｸ企剞",
            min_value=1,
            value=30,
            step=1,
            key="competitor_max_handling_count",
            disabled=not exclude_large,
        )
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="competitor_clear"):
            reset_form(COMPETITOR_STATE_KEYS)
            st.rerun()

    manufacturer_query = str(manufacturer_query).strip()
    search_clicked = st.button("謗ｨ螳夂ｫｶ蜷医ｒ讀懃ｴ｢", key="competitor_search")

    if not manufacturer_query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪ｒ驕ｸ謚槭☆繧九→縲∝・騾壻ｻ｣逅・ｺ励・繝ｼ繧ｹ縺ｮ謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ荳隕ｧ繧定｡ｨ遉ｺ縺励∪縺吶・)
        return

    if not search_clicked:
        st.caption("讀懃ｴ｢繝懊ち繝ｳ繧呈款縺吶→縲・∈謚槭Γ繝ｼ繧ｫ繝ｼ縺ｨ蜷後§莉｣逅・ｺ励〒謇ｱ繧上ｌ縺ｦ縺・ｋ莉悶Γ繝ｼ繧ｫ繝ｼ繧偵せ繧ｳ繧｢蛹悶＠縺ｦ荳ｦ縺ｹ縺ｾ縺吶・)
        return

    results = get_competitor_candidates(
        manufacturer_query,
        data["relations"],
        data["handlings"],
        max_handling_count=int(max_handling_count) if exclude_large else None,
    )

    if not results:
        st.warning("謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ縺ｯ0莉ｶ縺ｧ縺励◆縲る勁螟匁擅莉ｶ繧堤ｷｩ繧√ｋ縺九∝挨縺ｮ繝｡繝ｼ繧ｫ繝ｼ縺ｧ遒ｺ隱阪＠縺ｦ縺上□縺輔＞縲・)
        return

    result_frame = pd.DataFrame(
        [
            {
                "鬆・ｽ・: item.rank,
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・: item.candidate_manufacturer_name,
                "蜈ｱ騾壻ｻ｣逅・ｺ玲焚": item.common_distributor_count,
                "驕ｸ謚槭Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚": item.base_manufacturer_distributor_count,
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚": item.candidate_manufacturer_distributor_count,
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢": f"{item.basic_score:.2f}",
                "鬘樔ｼｼ蠎ｦ繧ｹ繧ｳ繧｢": f"{item.similarity_score:.2f}",
                "蜈ｱ騾壻ｻ｣逅・ｺ嶺ｸ隕ｧ": ", ".join(item.common_distributors),
            }
            for item in results[:50]
        ]
    )

    candidate_filter = st.text_input(
        "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷阪〒邨槭ｊ霎ｼ縺ｿ",
        placeholder="萓・ 繧ｪ繝繝ｭ繝ｳ / 荳芽廠 / SMC",
        key="competitor_candidate_filter",
    ).strip()
    if candidate_filter:
        result_frame = result_frame[
            result_frame["蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・].str.contains(candidate_filter, case=False, na=False)
        ].copy()

    st.write(f"謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ: {len(result_frame)}莉ｶ")
    render_link_table(
        result_frame[
            [
                "鬆・ｽ・,
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・,
                "蜈ｱ騾壻ｻ｣逅・ｺ玲焚",
                "驕ｸ謚槭Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚",
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚",
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢",
                "鬘樔ｼｼ蠎ｦ繧ｹ繧ｳ繧｢",
                "蜈ｱ騾壻ｻ｣逅・ｺ嶺ｸ隕ｧ",
            ]
        ]
    )
    render_unified_download(result_frame, file_name="competitor_candidates_results.csv")


def main() -> None:
    st.set_page_config(
        page_title="indexPro 莉募・蜈域､懃ｴ｢",
        page_icon=":material/account_tree:",
        layout="wide",
    )

    st.title("indexPro 莉募・蜈域､懃ｴ｢")
    st.caption("莨∵･ｭ讀懃ｴ｢縲√Γ繝ｼ繧ｫ繝ｼ讀懃ｴ｢縲∽ｻ｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢縲∵耳螳壻ｻ｣逅・ｺ玲､懃ｴ｢縲∵耳螳夂ｫｶ蜷域､懃ｴ｢繧・縺､縺ｮ逕ｻ髱｢縺ｧ遒ｺ隱阪〒縺阪∪縺吶・)

    require_login()

    missing = find_missing_files()
    if missing:
        st.error("蠢・ｦ√↑CSV縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲ょ・縺ｫ荳隕ｧ蜿門ｾ励ｒ螳溯｡後＠縺ｦ縺上□縺輔＞縲・)
        for path in missing:
            st.code(str(path))
        st.stop()

    data = load_app_data()
    render_summary(data)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["莨∵･ｭ讀懃ｴ｢", "繝｡繝ｼ繧ｫ繝ｼ讀懃ｴ｢", "莉｣逅・ｺ励・蜿匁桶蠎玲､懃ｴ｢", "謗ｨ螳壻ｻ｣逅・ｺ玲､懃ｴ｢", "謗ｨ螳夂ｫｶ蜷域､懃ｴ｢"]
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
    st.subheader("繝｡繝ｼ繧ｫ繝ｼ縺九ｉ謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ繧呈爾縺・)

    manufacturers = build_manufacturer_metadata(data["manufacturers"].copy(), data["labels"])
    manufacturer_options = [""] + sorted(
        manufacturers["manufacturer_name"].dropna().astype(str).drop_duplicates().tolist()
    )

    input_col1, input_col2, input_col3, button_col = st.columns([3, 2, 2, 1])
    with input_col1:
        manufacturer_query = st.selectbox(
            "繝｡繝ｼ繧ｫ繝ｼ蜷・,
            manufacturer_options,
            index=0,
            key="competitor_manufacturer_query",
            format_func=lambda value: value or "驕ｸ謚槭＠縺ｦ縺上□縺輔＞",
        )
    with input_col2:
        exclude_large = st.checkbox(
            "蜿匁桶繝｡繝ｼ繧ｫ繝ｼ謨ｰ縺悟､壹☆縺弱ｋ莉｣逅・ｺ励ｒ髯､螟・,
            value=True,
            key="competitor_max_handling_enabled",
        )
    with input_col3:
        max_handling_count = st.number_input(
            "髯､螟紋ｸ企剞",
            min_value=1,
            value=30,
            step=1,
            key="competitor_max_handling_count",
            disabled=not exclude_large,
        )
    with button_col:
        st.write("")
        if st.button("繧ｯ繝ｪ繧｢", key="competitor_clear"):
            reset_form(COMPETITOR_STATE_KEYS)
            st.rerun()

    manufacturer_query = str(manufacturer_query).strip()
    search_clicked = st.button("謗ｨ螳夂ｫｶ蜷医ｒ讀懃ｴ｢", key="competitor_search")

    if not manufacturer_query:
        st.info("繝｡繝ｼ繧ｫ繝ｼ蜷阪ｒ驕ｸ謚槭☆繧九→縲∝・騾壻ｻ｣逅・ｺ励・繝ｼ繧ｹ縺ｮ謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ荳隕ｧ繧定｡ｨ遉ｺ縺励∪縺吶・)
        return

    if not search_clicked:
        st.caption("讀懃ｴ｢繝懊ち繝ｳ繧呈款縺吶→縲・∈謚槭Γ繝ｼ繧ｫ繝ｼ縺ｨ蜷後§莉｣逅・ｺ励〒謇ｱ繧上ｌ縺ｦ縺・ｋ莉悶Γ繝ｼ繧ｫ繝ｼ繧偵せ繧ｳ繧｢蛹悶＠縺ｦ荳ｦ縺ｹ縺ｾ縺吶・)
        return

    results = get_competitor_candidates(
        manufacturer_query,
        data["relations"],
        data["handlings"],
        max_handling_count=int(max_handling_count) if exclude_large else None,
    )

    if not results:
        st.warning("謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ縺ｯ0莉ｶ縺ｧ縺励◆縲る勁螟匁擅莉ｶ繧堤ｷｩ繧√ｋ縺九∝挨縺ｮ繝｡繝ｼ繧ｫ繝ｼ縺ｧ遒ｺ隱阪＠縺ｦ縺上□縺輔＞縲・)
        return

    result_frame = pd.DataFrame(
        [
            {
                "鬆・ｽ・: item.rank,
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・: item.candidate_manufacturer_name,
                "蜈ｱ騾壻ｻ｣逅・ｺ玲焚": item.common_distributor_count,
                "驕ｸ謚槭Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚": item.base_manufacturer_distributor_count,
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚": item.candidate_manufacturer_distributor_count,
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢": f"{item.basic_score:.2f}",
                "鬘樔ｼｼ蠎ｦ繧ｹ繧ｳ繧｢": f"{item.similarity_score:.2f}",
                "蜈ｱ騾壻ｻ｣逅・ｺ嶺ｸ隕ｧ": ", ".join(item.common_distributors),
            }
            for item in results[:50]
        ]
    )
    result_frame = result_frame.merge(
        manufacturers[["manufacturer_name", "manufacturer_page_url"]].drop_duplicates(subset=["manufacturer_name"]),
        how="left",
        left_on="蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・,
        right_on="manufacturer_name",
    )

    candidate_filter = st.text_input(
        "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷阪〒邨槭ｊ霎ｼ縺ｿ",
        placeholder="萓・ 繧ｪ繝繝ｭ繝ｳ / 荳芽廠 / SMC",
        key="competitor_candidate_filter",
    ).strip()
    if candidate_filter:
        result_frame = result_frame[
            result_frame["蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・].str.contains(candidate_filter, case=False, na=False)
        ].copy()

    st.write(f"謗ｨ螳夂ｫｶ蜷医Γ繝ｼ繧ｫ繝ｼ: {len(result_frame)}莉ｶ")
    render_link_table(
        result_frame[
            [
                "鬆・ｽ・,
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ蜷・,
                "蜈ｱ騾壻ｻ｣逅・ｺ玲焚",
                "驕ｸ謚槭Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚",
                "蛟呵｣懊Γ繝ｼ繧ｫ繝ｼ莉｣逅・ｺ玲焚",
                "蝓ｺ譛ｬ繧ｹ繧ｳ繧｢",
                "鬘樔ｼｼ蠎ｦ繧ｹ繧ｳ繧｢",
                "manufacturer_page_url",
                "蜈ｱ騾壻ｻ｣逅・ｺ嶺ｸ隕ｧ",
            ]
        ],
        link_columns={"manufacturer_page_url": "indexPro 繝｡繝ｼ繧ｫ繝ｼ繝壹・繧ｸ"},
    )
    render_unified_download(result_frame, file_name="competitor_candidates_results.csv")


def render_summary(data: dict[str, pd.DataFrame]) -> None:
    metrics = metrics_to_map(data["metrics"])
    validation = metrics_to_map(data["validation"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("繝｡繝ｼ繧ｫ繝ｼ謨ｰ", metrics.get("manufacturer_count", "-"))
    col2.metric("莉｣逅・ｺ玲焚", metrics.get("distributor_count", "-"))
    col3.metric("蜿匁桶髢｢菫よ焚", metrics.get("handling_relation_count", "-"))
    col4.metric("譛ｪ荳閾ｴ莉ｶ謨ｰ", validation.get("handling_unmatched", "-"))


def format_generated_date(value: str) -> str:
    text = str(value or "").strip()
    if "T" in text:
        return text.split("T", 1)[0]
    if " " in text:
        return text.split(" ", 1)[0]
    return text


@st.cache_data(show_spinner=False)
def load_deploy_trigger() -> dict[str, str]:
    if not DEPLOY_TRIGGER_FILE.exists():
        return {}

    values: dict[str, str] = {}
    for line in DEPLOY_TRIGGER_FILE.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def render_footer(data: dict[str, pd.DataFrame]) -> None:
    st.divider()
    metrics = metrics_to_map(data["metrics"])
    deploy_info = load_deploy_trigger()
    deploy_date = format_generated_date(deploy_info.get("last_redeploy_utc", ""))
    generated_date = format_generated_date(metrics.get("generated_at", ""))
    display_date = deploy_date or generated_date
    suffix = f" 譛邨よ峩譁ｰ譌･: {display_date}" if display_date else ""
    st.caption(
        "Copyright (c) 2026 Tomoki Hotei. "
        "遉ｾ蜀・茜逕ｨ蜷代￠隧ｦ菴懃沿縲ょ・髢区ュ蝣ｱ繧貞・縺ｫ菴懈・縺励※縺翫ｊ縲∝・螳ｹ縺ｮ豁｣遒ｺ諤ｧ繝ｻ螳悟・諤ｧ繧剃ｿ晁ｨｼ縺吶ｋ繧ゅ・縺ｧ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・
        + suffix
    )


if __name__ == "__main__":
    main()

