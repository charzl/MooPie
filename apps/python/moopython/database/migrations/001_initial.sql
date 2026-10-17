-- Original snapshot schema. Published migrations are append-only.
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY,
    request_key TEXT NOT NULL,
    session_date TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    checksum TEXT NOT NULL,
    payload BLOB NOT NULL
);

CREATE INDEX snapshot_lookup
    ON snapshots(request_key, session_date, fetched_at DESC, id DESC);
