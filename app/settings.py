from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DB_DIR = OUTPUT_DIR / "db"
INDEXPRO_DIR = OUTPUT_DIR / "indexpro"
INDEXPRO_LISTINGS_DIR = INDEXPRO_DIR / "listings"
INDEXPRO_VALIDATION_DIR = INDEXPRO_DIR / "validation"
LATEST_DIR = INDEXPRO_LISTINGS_DIR
INDEXPRO_DIRECTORY_FIXTURE_PATH = DATA_DIR / "fixtures" / "indexpro_directory_sample.json"

GOOGLE_SHEETS_SPREADSHEET_ID = "11EzN77QBYvRN0DKpok5KVNK-DMMG1WbhHqNj1b6anLI"


def build_google_sheet_csv_url(gid: str | int) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_SPREADSHEET_ID}/export"
        f"?format=csv&gid={gid}"
    )


INDEXPRO_DIRECTORY_DISTRIBUTORS_SOURCE = build_google_sheet_csv_url("940598707")
INDEXPRO_DIRECTORY_HANDLINGS_SOURCE = build_google_sheet_csv_url("905352575")
INDEXPRO_DIRECTORY_MANUFACTURERS_SOURCE = build_google_sheet_csv_url("599388913")
INDEXPRO_DIRECTORY_METRICS_SOURCE = build_google_sheet_csv_url("334244826")
INDEXPRO_DIRECTORY_RELATIONS_SOURCE = build_google_sheet_csv_url("853616432")


@dataclass(slots=True)
class AppSettings:
    database_path: Path = DB_DIR / "supplier_flow.db"
    request_timeout_seconds: int = 15
    crawl_delay_seconds: float = 0.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    INDEXPRO_DIR.mkdir(parents=True, exist_ok=True)
    INDEXPRO_LISTINGS_DIR.mkdir(parents=True, exist_ok=True)
    INDEXPRO_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
