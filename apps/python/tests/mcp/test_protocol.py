import os
from pathlib import Path
import sys
import unittest
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[2]


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_discovery_tools_schema_and_provider_errors(self):
        params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name('fixture_server.py'))],
                                       env=dict(os.environ, PYTHONPATH=str(ROOT)))
        async with Client(params, read_timeout_seconds=15) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual({tool.name for tool in tools}, {'get_market_snapshots', 'get_option_chain', 'get_daily_bars', 'get_earnings_calendar'})
            self.assertTrue(all(tool.annotations.read_only_hint for tool in tools))
            self.assertTrue(all(tool.annotations.destructive_hint is False for tool in tools))
            for name, arguments, operation in [
                ('get_market_snapshots', {'codes': ['US.AVGO']}, 'snapshots'),
                ('get_option_chain', {'symbol': 'AVGO', 'months': 3}, 'option_chain'),
                ('get_daily_bars', {'symbols': ['NVDA']}, 'daily_bars'),
                ('get_earnings_calendar', {'start': '2026-10-16', 'end': '2026-10-22'}, 'earnings_calendar')]:
                result = await client.call_tool(name, arguments)
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content['operation'], operation)
                self.assertEqual(result.structured_content['source'], 'synthetic protocol fixture')
            bad = await client.call_tool('get_market_snapshots', {'codes': ['US.FAIL']})
            self.assertTrue(bad.is_error)
            malformed = await client.call_tool('get_market_snapshots', {'codes': 3})
            self.assertTrue(malformed.is_error)
            # Provider / validation failures must not kill the MCP process.
            healthy = await client.call_tool('get_market_snapshots', {'codes': ['US.NVDA']})
            self.assertFalse(healthy.is_error)


if __name__ == '__main__': unittest.main()
