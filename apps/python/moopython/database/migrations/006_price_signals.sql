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
CREATE INDEX price_signals_latest ON price_signals(symbol, as_of DESC, calculated_at DESC);
