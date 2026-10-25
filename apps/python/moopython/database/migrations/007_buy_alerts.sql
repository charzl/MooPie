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
);
