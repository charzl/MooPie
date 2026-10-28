CREATE TABLE support_studies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of TEXT NOT NULL,
    study_version TEXT NOT NULL,
    definition_key TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (symbol, as_of, definition_key, input_hash)
);
CREATE INDEX support_studies_latest
    ON support_studies(symbol, as_of DESC, calculated_at DESC, id DESC);
