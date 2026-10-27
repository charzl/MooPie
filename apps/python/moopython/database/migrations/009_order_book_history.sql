CREATE TABLE order_book_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    quote_time TEXT,
    payload TEXT NOT NULL,
    UNIQUE(symbol, collected_at)
);
CREATE INDEX order_book_history_symbol_time
    ON order_book_history(symbol, collected_at DESC);
