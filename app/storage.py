from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .indexpro_directory import IndexProDirectoryResult
from .models import RawPage


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer_name TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    body TEXT,
    domain TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexpro_listing_manufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer_name TEXT NOT NULL,
    initial TEXT NOT NULL,
    mcid TEXT NOT NULL,
    distributor_list_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexpro_listing_distributors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    distributor_name TEXT NOT NULL,
    initial TEXT NOT NULL,
    did TEXT NOT NULL,
    source_category TEXT NOT NULL,
    company_url TEXT NOT NULL,
    location_url TEXT NOT NULL,
    online_sales_url TEXT NOT NULL,
    handling_makers_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexpro_listing_handlings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    did TEXT NOT NULL,
    distributor_name TEXT NOT NULL,
    handling_manufacturer_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexpro_listing_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mcid TEXT NOT NULL,
    manufacturer_name TEXT NOT NULL,
    distributor_name TEXT NOT NULL,
    did TEXT NOT NULL,
    relation_category TEXT NOT NULL,
    company_url TEXT NOT NULL,
    location_url TEXT NOT NULL,
    online_sales_url TEXT NOT NULL
);
"""


class SQLiteStorage:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA_SQL)
        self._migrate_schema()
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _migrate_schema(self) -> None:
        distributor_columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(indexpro_listing_distributors)")
        }
        if "location_url" not in distributor_columns:
            self.connection.execute(
                """
                ALTER TABLE indexpro_listing_distributors
                ADD COLUMN location_url TEXT NOT NULL DEFAULT ''
                """
            )
        if "online_sales_url" not in distributor_columns:
            self.connection.execute(
                """
                ALTER TABLE indexpro_listing_distributors
                ADD COLUMN online_sales_url TEXT NOT NULL DEFAULT ''
                """
            )
        if "source_category" not in distributor_columns:
            self.connection.execute(
                """
                ALTER TABLE indexpro_listing_distributors
                ADD COLUMN source_category TEXT NOT NULL DEFAULT '代理店・取扱店'
                """
            )

    def save_raw_pages(self, raw_pages: Iterable[RawPage]) -> None:
        rows = [
            (
                page.manufacturer_name,
                page.url,
                page.title,
                page.body,
                page.domain,
                page.fetched_at.isoformat(),
            )
            for page in raw_pages
        ]
        self.connection.executemany(
            """
            INSERT INTO raw_pages (
                manufacturer_name, url, title, body, domain, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.connection.commit()

    def save_indexpro_listing_result(self, result: IndexProDirectoryResult) -> None:
        self.connection.executemany(
            """
            INSERT INTO indexpro_listing_manufacturers (
                manufacturer_name, initial, mcid, distributor_list_url
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    item.name,
                    item.initial,
                    item.mcid,
                    item.distributor_list_url,
                )
                for item in result.manufacturers
            ],
        )
        self.connection.executemany(
            """
            INSERT INTO indexpro_listing_distributors (
                distributor_name, initial, did, source_category, company_url, location_url, online_sales_url, handling_makers_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.name,
                    item.initial,
                    item.did,
                    item.source_category,
                    item.company_url,
                    item.location_url,
                    item.online_sales_url,
                    item.handling_makers_url,
                )
                for item in result.distributors
            ],
        )
        self.connection.executemany(
            """
            INSERT INTO indexpro_listing_handlings (
                did, distributor_name, handling_manufacturer_name
            ) VALUES (?, ?, ?)
            """,
            [
                (
                    item.did,
                    item.distributor_name,
                    item.handling_manufacturer_name,
                )
                for item in result.handlings
            ],
        )
        self.connection.executemany(
            """
            INSERT INTO indexpro_listing_relations (
                mcid, manufacturer_name, distributor_name, did, relation_category, company_url, location_url, online_sales_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.mcid,
                    item.manufacturer_name,
                    item.distributor_name,
                    item.did,
                    item.relation_category,
                    item.company_url,
                    item.location_url,
                    item.online_sales_url,
                )
                for item in result.relations
            ],
        )
        self.connection.commit()
