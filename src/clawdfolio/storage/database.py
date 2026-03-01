"""SQLite database connection management and schema migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "~/.cache/clawdfolio/portfolio_history.db"

SCHEMA_VERSION = 1

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    net_assets REAL NOT NULL,
    cash REAL NOT NULL,
    market_value REAL NOT NULL,
    day_pnl REAL NOT NULL,
    source TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS position_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    market_value REAL NOT NULL,
    weight REAL NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
    ON portfolio_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_positions_snapshot_id
    ON position_snapshots(snapshot_id);
"""


def get_db_path(path: str | None = None) -> Path:
    """Resolve database file path."""
    p = Path(path or DEFAULT_DB_PATH).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_connection(path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection, creating/migrating schema as needed."""
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn


def init_db(path: str | None = None) -> Path:
    """Initialize the database and return its path."""
    conn = get_connection(path)
    conn.close()
    return get_db_path(path)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist and handle migrations."""
    cursor = conn.cursor()

    # Check if schema_version table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    if not cursor.fetchone():
        # Fresh database — create everything
        conn.executescript(SCHEMA_SQL)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
        return

    # Check current version
    row = cursor.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    current = row[0] if row else 0

    if current < SCHEMA_VERSION:
        # Future migrations go here
        conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
        conn.commit()
