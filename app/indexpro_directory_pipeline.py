from __future__ import annotations

from .indexpro_directory import IndexProDirectoryResult, fetch_directory_live, load_directory_fixture
from .indexpro_directory_reporting import write_directory_outputs
from .settings import INDEXPRO_DIRECTORY_FIXTURE_PATH, LATEST_DIR, AppSettings, ensure_output_dirs
from .storage import SQLiteStorage


def run_indexpro_directory_pipeline(mode: str, settings: AppSettings) -> IndexProDirectoryResult:
    ensure_output_dirs()
    storage = SQLiteStorage(settings.database_path)
    try:
        if mode == "indexpro-directory-fixture":
            result = load_directory_fixture(INDEXPRO_DIRECTORY_FIXTURE_PATH)
        else:
            result = fetch_directory_live(settings)
        storage.save_indexpro_listing_result(result)
        write_directory_outputs(LATEST_DIR, result)
        return result
    finally:
        storage.close()
