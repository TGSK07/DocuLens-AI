"""SQLite-backed extraction store + on-disk file layout."""
from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _make_id() -> str:
    return secrets.token_urlsafe(9)


@dataclass(frozen=True)
class Extraction:
    id: str
    filename: str
    schema_key: str
    schema_label: str
    page_count: int
    data_json: str
    custom_schema_json: str | None
    tokens_input: int
    tokens_output: int
    duration_ms: int
    created_at: str

    @property
    def data(self) -> dict[str, Any]:
        try:
            return json.loads(self.data_json)
        except Exception:
            return {}


# ─────────────────────────── Connection ───────────────────────────

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(
            settings.database_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode = WAL")
        _connection.execute("PRAGMA foreign_keys = ON")
        _connection.execute("PRAGMA synchronous = NORMAL")
    return _connection


def init_schema() -> None:
    db = get_connection()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS extractions (
            id                 TEXT    PRIMARY KEY,
            filename           TEXT    NOT NULL,
            schema_key         TEXT    NOT NULL,
            schema_label       TEXT    NOT NULL,
            page_count         INTEGER NOT NULL,
            data_json          TEXT    NOT NULL,
            custom_schema_json TEXT,
            tokens_input       INTEGER NOT NULL DEFAULT 0,
            tokens_output      INTEGER NOT NULL DEFAULT 0,
            duration_ms        INTEGER NOT NULL DEFAULT 0,
            created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS extractions_created
            ON extractions(created_at DESC);
        """
    )
    db.commit()


# ─────────────────────────── On-disk layout ───────────────────────────

def extraction_dir(extraction_id: str) -> Path:
    """Folder where the original upload + page PNGs live."""
    d = settings.extractions_dir / extraction_id
    (d / "pages").mkdir(parents=True, exist_ok=True)
    return d


def original_path(extraction_id: str, suffix: str) -> Path:
    return extraction_dir(extraction_id) / f"original{suffix}"


def page_path(extraction_id: str, page_number: int) -> Path:
    return extraction_dir(extraction_id) / "pages" / f"{page_number}.png"


# ─────────────────────────── Queries ───────────────────────────

def create_extraction(
    filename: str,
    schema_key: str,
    schema_label: str,
    page_count: int,
    data: dict[str, Any],
    custom_schema: dict[str, Any] | None,
    tokens_input: int,
    tokens_output: int,
    duration_ms: int,
) -> str:
    db = get_connection()
    eid = _make_id()
    db.execute(
        """
        INSERT INTO extractions
            (id, filename, schema_key, schema_label, page_count, data_json,
             custom_schema_json, tokens_input, tokens_output, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eid,
            filename,
            schema_key,
            schema_label,
            page_count,
            json.dumps(data, default=str),
            json.dumps(custom_schema) if custom_schema is not None else None,
            tokens_input,
            tokens_output,
            duration_ms,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    return eid


def get_extraction(extraction_id: str) -> Extraction | None:
    db = get_connection()
    row = db.execute("SELECT * FROM extractions WHERE id = ?", (extraction_id,)).fetchone()
    if not row:
        return None
    return _row_to_extraction(row)


def list_recent_extractions(limit: int = 30) -> list[Extraction]:
    db = get_connection()
    rows = db.execute(
        "SELECT * FROM extractions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [_row_to_extraction(r) for r in rows]


def update_extraction_data(extraction_id: str, data: dict[str, Any]) -> bool:
    db = get_connection()
    cur = db.execute(
        "UPDATE extractions SET data_json = ? WHERE id = ?",
        (json.dumps(data, default=str), extraction_id),
    )
    db.commit()
    return cur.rowcount > 0


def delete_extraction(extraction_id: str) -> bool:
    db = get_connection()
    cur = db.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))
    db.commit()
    return cur.rowcount > 0


def _row_to_extraction(row: sqlite3.Row) -> Extraction:
    return Extraction(
        id=row["id"],
        filename=row["filename"],
        schema_key=row["schema_key"],
        schema_label=row["schema_label"],
        page_count=row["page_count"],
        data_json=row["data_json"],
        custom_schema_json=row["custom_schema_json"],
        tokens_input=row["tokens_input"],
        tokens_output=row["tokens_output"],
        duration_ms=row["duration_ms"],
        created_at=row["created_at"],
    )
