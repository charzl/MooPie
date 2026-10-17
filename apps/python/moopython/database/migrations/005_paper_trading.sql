CREATE TABLE paper_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('forward','backtest')),
    created_at TEXT NOT NULL,
    configuration TEXT NOT NULL,
    state TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE paper_clients (
    experiment_id INTEGER NOT NULL REFERENCES paper_experiments(id),
    client_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    PRIMARY KEY (experiment_id,client_id)
);
CREATE TABLE paper_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES paper_experiments(id),
    observed_at TEXT NOT NULL,
    checksum TEXT NOT NULL,
    payload BLOB NOT NULL
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
CREATE TABLE paper_valuations (
    experiment_id INTEGER NOT NULL,
    client_id TEXT NOT NULL,
    session_date TEXT NOT NULL,
    input_id INTEGER NOT NULL REFERENCES paper_inputs(id),
    evidence TEXT NOT NULL,
    PRIMARY KEY (experiment_id,client_id,session_date),
    FOREIGN KEY (experiment_id,client_id) REFERENCES paper_clients(experiment_id,client_id)
);
CREATE INDEX paper_fills_experiment_date ON paper_fills(experiment_id,session_date);
CREATE INDEX paper_inputs_experiment ON paper_inputs(experiment_id,id);
