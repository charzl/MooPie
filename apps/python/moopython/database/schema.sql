-- Generated from moopython/database/migrations; do not edit.
-- Inspect only: existing databases are upgraded by the application.

CREATE TABLE buy_alerts (
    symbol TEXT PRIMARY KEY,
    support_low REAL NOT NULL CHECK (support_low > 0),
    support_high REAL NOT NULL CHECK (support_high >= support_low),
    signal_as_of TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('watching', 'inside', 'confirmed', 'invalidated', 'paused')),
    last_quote_time TEXT NOT NULL DEFAULT '',
    last_price REAL,
    triggered_at TEXT,
    updated_at TEXT NOT NULL
, confirmation_mode TEXT NOT NULL DEFAULT 'quote'
    CHECK (confirmation_mode IN ('quote', 'daily_close')), entered_at TEXT NOT NULL DEFAULT '', last_bar_date TEXT NOT NULL DEFAULT '');

CREATE TABLE order_book_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    quote_time TEXT,
    payload TEXT NOT NULL,
    UNIQUE(symbol, collected_at)
);

CREATE TABLE paper_clients (
    experiment_id INTEGER NOT NULL REFERENCES paper_experiments(id),
    client_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    PRIMARY KEY (experiment_id,client_id)
);

CREATE TABLE paper_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('forward','backtest')),
    created_at TEXT NOT NULL,
    configuration TEXT NOT NULL,
    state TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE paper_fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    client_id TEXT NOT NULL,
    session_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    quantity REAL NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price > 0),
    fee REAL NOT NULL CHECK (fee >= 0),
    input_id INTEGER NOT NULL REFERENCES paper_inputs(id),
    evidence TEXT NOT NULL,
    FOREIGN KEY (experiment_id,client_id) REFERENCES paper_clients(experiment_id,client_id),
    UNIQUE (experiment_id,client_id,session_date,symbol,side)
);

CREATE TABLE paper_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES paper_experiments(id),
    observed_at TEXT NOT NULL,
    checksum TEXT NOT NULL,
    payload BLOB NOT NULL
);

CREATE TABLE paper_valuations (
    experiment_id INTEGER NOT NULL,
    client_id TEXT NOT NULL,
    session_date TEXT NOT NULL,
    input_id INTEGER NOT NULL REFERENCES paper_inputs(id),
    evidence TEXT NOT NULL,
    PRIMARY KEY (experiment_id,client_id,session_date),
    FOREIGN KEY (experiment_id,client_id) REFERENCES paper_clients(experiment_id,client_id)
);

CREATE TABLE price_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of TEXT NOT NULL,
    reference_price REAL NOT NULL CHECK (reference_price > 0),
    reference_time TEXT NOT NULL,
    signal_version TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (symbol, as_of, reference_time, signal_version)
);

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

CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE INDEX order_book_history_symbol_time
    ON order_book_history(symbol, collected_at DESC);

CREATE INDEX paper_fills_experiment_date ON paper_fills(experiment_id,session_date);

CREATE INDEX paper_inputs_experiment ON paper_inputs(experiment_id,id);

CREATE INDEX price_signals_latest ON price_signals(symbol, as_of DESC, calculated_at DESC);

CREATE INDEX security_alias_lookup ON security_aliases(normalized_alias COLLATE NOCASE);

CREATE INDEX security_name ON securities(normalized_name COLLATE NOCASE);

CREATE INDEX security_ticker ON securities(ticker COLLATE NOCASE);

CREATE INDEX snapshot_batch ON snapshots(batch_id);

CREATE INDEX snapshot_lookup
    ON snapshots(request_key, session_date, fetched_at DESC, id DESC);

CREATE INDEX snapshot_retention ON snapshots(fetched_at);

CREATE INDEX snapshot_symbol_time
    ON snapshots(symbol, operation, session_date, fetched_at DESC);

CREATE INDEX support_studies_latest
    ON support_studies(symbol, as_of DESC, calculated_at DESC, id DESC);

PRAGMA user_version=10;
