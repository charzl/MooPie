"""Versioned SQLite definitions shared by source, wheel and desktop installs."""
from contextlib import closing
from pathlib import Path
import sqlite3


SCHEMA_VERSION = 10
ROOT = Path(__file__).resolve().parent
MIGRATIONS = ('001_initial.sql', '002_snapshot_metadata.sql', '003_security_directory.sql', '004_watchlist.sql', '005_paper_trading.sql', '006_price_signals.sql', '007_buy_alerts.sql', '008_alert_confirmation.sql', '009_order_book_history.sql', '010_support_studies.sql')


def _execute(connection, script):
    # executescript() commits a pending transaction. Execute complete statements
    # separately so DDL, data conversion and user_version all roll back together.
    statement = ''
    for character in script:
        statement += character
        if character == ';' and sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ''
    if statement.strip():
        raise RuntimeError('Incomplete SQL statement in database migration')


def migrate(connection, metadata):
    """Apply pending versions inside the caller's exclusive writer transaction."""
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    if not 0 <= version <= SCHEMA_VERSION:
        raise RuntimeError('Unsupported market database schema; use the matching application version')
    for target in range(version + 1, SCHEMA_VERSION + 1):
        script = (ROOT / 'migrations' / MIGRATIONS[target - 1]).read_text(encoding='utf-8')
        _execute(connection, script)
        if target == 2:
            # JSON request keys need a Python conversion; compressed payloads
            # and original IDs are copied unchanged by the SQL migration.
            for snapshot_id, key in connection.execute('SELECT id, request_key FROM snapshots').fetchall():
                symbol, operation = metadata(key)
                connection.execute('UPDATE snapshots SET symbol=?, operation=? WHERE id=?',
                                   (symbol, operation, snapshot_id))
        connection.execute(f'PRAGMA user_version={target}')


def schema_sql():
    """Generate the current schema from migrations without opening user data."""
    with closing(sqlite3.connect(':memory:')) as connection:
        connection.execute('BEGIN IMMEDIATE')
        with connection:
            migrate(connection, lambda key: (None, 'unknown'))
        definitions = [row[0] + ';' for row in connection.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
            "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name")]
    return ('-- Generated from moopython/database/migrations; do not edit.\n'
            '-- Inspect only: existing databases are upgraded by the application.\n\n'
            + '\n\n'.join(definitions) + f'\n\nPRAGMA user_version={SCHEMA_VERSION};\n')
