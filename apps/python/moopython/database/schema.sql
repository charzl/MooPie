-- Generated from moopython/database/migrations; do not edit.
-- Inspect only: existing databases are upgraded by the application.

CREATE TABLE securities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    ticker TEXT NOT NULL COLLATE NOCASE,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL COLLATE NOCASE,
    security_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'delisted')),
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE security_aliases (
    security_id INTEGER NOT NULL REFERENCES securities(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL COLLATE NOCASE,
    alias_type TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (security_id, normalized_alias)
);

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_key TEXT NOT NULL,
    session_date TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    checksum TEXT NOT NULL,
    payload BLOB NOT NULL,
    symbol TEXT,
    operation TEXT NOT NULL,
    batch_id TEXT NOT NULL
);

CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE INDEX security_alias_lookup ON security_aliases(normalized_alias COLLATE NOCASE);

CREATE INDEX security_name ON securities(normalized_name COLLATE NOCASE);

CREATE INDEX security_ticker ON securities(ticker COLLATE NOCASE);

CREATE INDEX snapshot_batch ON snapshots(batch_id);

CREATE INDEX snapshot_lookup
    ON snapshots(request_key, session_date, fetched_at DESC, id DESC);

CREATE INDEX snapshot_retention ON snapshots(fetched_at);

CREATE INDEX snapshot_symbol_time
    ON snapshots(symbol, operation, session_date, fetched_at DESC);

PRAGMA user_version=4;
