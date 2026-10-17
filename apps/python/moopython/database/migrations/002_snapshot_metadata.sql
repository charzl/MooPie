-- Preserve old IDs and compressed bytes; the Python migration hook derives
-- symbol and operation from request_key before committing the new version.
ALTER TABLE snapshots RENAME TO snapshots_v1;

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

INSERT INTO snapshots
    (id, request_key, session_date, fetched_at, saved_at, checksum, payload, operation, batch_id)
    SELECT id, request_key, session_date, fetched_at, saved_at, checksum, payload,
           'legacy', 'legacy-' || id FROM snapshots_v1;

DROP TABLE snapshots_v1;

CREATE INDEX snapshot_lookup
    ON snapshots(request_key, session_date, fetched_at DESC, id DESC);

CREATE INDEX snapshot_retention ON snapshots(fetched_at);

CREATE INDEX snapshot_symbol_time
    ON snapshots(symbol, operation, session_date, fetched_at DESC);

CREATE INDEX snapshot_batch ON snapshots(batch_id);

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
