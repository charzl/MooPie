"""Thin, read-only MCP adapter over the same collection API used by the CLI."""
import argparse
from contextlib import contextmanager, redirect_stdout
import sys
import threading
import time
from typing import Any

from .market_collection import opend_connection
from .market_repository import market_data_connection


class OpenDReader:
    """Serialize SDK calls and keep SDK diagnostics off the MCP stdio channel."""
    def __init__(self, host='127.0.0.1', port=11111, connection=opend_connection, *, store=None, clock=None):
        self.host, self.port, self.connection = host, port, connection
        self.store, self.clock = store, clock
        self.lock = threading.Lock()
        self.last_finished = float('-inf')

    @contextmanager
    def live_connection(self, **parameters):
        # Rate limits apply to actual provider requests, never to database reads.
        time.sleep(max(0, 3.1 - (time.monotonic() - self.last_finished)))
        try:
            with self.connection(**parameters) as service:
                yield service
        finally:
            self.last_finished = time.monotonic()

    def __call__(self, operation, refresh=False, **parameters):
        if operation not in ('snapshots', 'option_chain', 'daily_bars', 'earnings_calendar'):
            raise ValueError('Unsupported read-only collection operation')
        with self.lock:
            with redirect_stdout(sys.stderr):
                with market_data_connection(self.host, self.port, store=self.store, clock=self.clock,
                                            refresh=refresh, connection=self.live_connection) as service:
                    return getattr(service, operation)(**parameters)


def register_tools(server, reader, annotations=None):
    """No SDK or storage calls during registration; reader is injectable in tests."""
    @server.tool(annotations=annotations)
    def get_market_snapshots(codes: list[str], refresh: bool = False) -> dict[str, Any]:
        """Fetch current US stock/option snapshots (1–200 codes), including bid/ask and option Greeks.

        Broker snapshot timestamps do not guarantee a fresh executable bid. Missing
        codes are explicit. After hours prefers SQLite and automatically fetches
        missing snapshots; refresh=true forces OpenD. data_access reports source and time.
        """
        return reader('snapshots', codes=codes, refresh=refresh)

    @server.tool(annotations=annotations)
    def get_option_chain(symbol: str, months: int = 1, option_type: str = 'PUT',
                         start: str | None = None, end: str | None = None,
                         refresh: bool = False) -> dict[str, Any]:
        """Fetch listed US option contracts and strikes, without strategy filters.

        Dates are YYYY-MM-DD, future expirations only. Prefer short explicit date
        windows to bound output size. months=1–24; option_type=PUT/CALL/ALL.
        This contract table contains no executable option quote; fetch snapshots next.
        After hours prefers SQLite, fetching missing data; refresh=true forces OpenD.
        """
        return reader('option_chain', symbol=symbol, months=months, option_type=option_type, start=start, end=end, refresh=refresh)

    @server.tool(annotations=annotations)
    def get_daily_bars(symbols: list[str], session_date: str | None = None,
                       cutoff: str | None = None, refresh: bool = False) -> dict[str, Any]:
        """Fetch about 380 completed regular-session QFQ daily bars per US symbol.

        Request a few symbols at a time (max 20). session_date is YYYY-MM-DD;
        cutoff is an optional timezone-aware ISO timestamp for historical research.
        Unfinished daily bars are excluded; gaps and provider errors stay visible.
        No RSI, trend judgment or strategy ranking is calculated here.
        After hours prefers SQLite, fetching missing data; refresh=true forces OpenD.
        """
        return reader('daily_bars', symbols=symbols, session_date=session_date, cutoff=cutoff, refresh=refresh)

    @server.tool(annotations=annotations)
    def get_earnings_calendar(start: str, end: str, refresh: bool = False) -> dict[str, Any]:
        """Fetch US provider earnings listings across 1–7 calendar days (YYYY-MM-DD).

        An absent listing means unknown; it never establishes earnings clearance.
        After hours prefers SQLite, fetching missing data; refresh=true forces OpenD.
        """
        return reader('earnings_calendar', start=start, end=end, refresh=refresh)
    return server


def create_server(reader=None):
    from mcp.server import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations
    server = MCPServer('moomoo-market-data')
    annotations = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=True)
    provider = reader or OpenDReader()
    def read(operation, **parameters):
        try:
            return provider(operation, **parameters)
        except (ValueError, RuntimeError, OSError) as error:
            raise ToolError(str(error)) from error
    return register_tools(server, read, annotations)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only OpenD MCP server using stdio; install the [mcp] extra')
    parser.add_argument('--host', choices=['127.0.0.1', 'localhost', '::1'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=11111)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535: parser.error('port must be 1–65535')
    try:
        server = create_server(OpenDReader(args.host, args.port))
    except ImportError:
        parser.exit(2, 'Install MCP support first: pip install "moomoo-clients[mcp]"\n')
    # SDK initialization may install signal handlers; import on the main thread.
    with redirect_stdout(sys.stderr):
        import moomoo  # noqa: F401
    server.run(transport='stdio')
    return 0


if __name__ == '__main__': raise SystemExit(main())
