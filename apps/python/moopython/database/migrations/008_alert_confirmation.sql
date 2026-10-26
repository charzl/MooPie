ALTER TABLE buy_alerts ADD COLUMN confirmation_mode TEXT NOT NULL DEFAULT 'quote'
    CHECK (confirmation_mode IN ('quote', 'daily_close'));
ALTER TABLE buy_alerts ADD COLUMN entered_at TEXT NOT NULL DEFAULT '';
ALTER TABLE buy_alerts ADD COLUMN last_bar_date TEXT NOT NULL DEFAULT '';
