"""Synthetic provider for protocol tests: never connects to OpenD."""
import sys
from moopython.market_mcp import create_server


def read(operation, **parameters):
    print('Synthetic provider log on stderr', file=sys.stderr)
    if operation == 'snapshots' and parameters['codes'] == ['US.FAIL']:
        raise RuntimeError('synthetic provider unavailable')
    return {'schema': 1, 'source': 'synthetic protocol fixture', 'operation': operation, 'parameters': parameters}


if __name__ == '__main__': create_server(read).run(transport='stdio')
