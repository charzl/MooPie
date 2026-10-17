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

CREATE INDEX security_ticker ON securities(ticker COLLATE NOCASE);

CREATE INDEX security_name ON securities(normalized_name COLLATE NOCASE);

CREATE TABLE security_aliases (
    security_id INTEGER NOT NULL REFERENCES securities(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL COLLATE NOCASE,
    alias_type TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (security_id, normalized_alias)
);

CREATE INDEX security_alias_lookup ON security_aliases(normalized_alias COLLATE NOCASE);
