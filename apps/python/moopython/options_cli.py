"""Query listed option strikes without starting Qt or launching OpenD."""
import argparse
from contextlib import redirect_stdout
from pathlib import Path
import socket
import signal
import sys

from .options import OptionQuery, OptionChainService, write_result


def main(argv=None):
    parser = argparse.ArgumentParser(description='查询股票 / ETF 的期权到期日与行权价（需先登录本机 OpenD）')
    parser.add_argument('symbol', help='例如 AAPL、US.NVDA、HK.00700；无市场前缀默认美股')
    parser.add_argument('--months', type=int, default=3, help='未来月份数，默认 3，范围 1–24')
    parser.add_argument('--start', help='到期日范围起点，YYYY-MM-DD，默认标的市场的今天')
    parser.add_argument('--end', help='到期日范围终点（含），默认起点之后 --months 个月')
    parser.add_argument('--type', choices=['ALL', 'CALL', 'PUT'], default='ALL')
    parser.add_argument('--host', choices=['127.0.0.1', 'localhost', '::1'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--format', choices=['json', 'csv'], default='json')
    parser.add_argument('--output', type=Path, help='保存文件；未指定时将结果写到标准输出')
    args = parser.parse_args(argv)
    context = None
    try:
        query = OptionQuery.upcoming(args.symbol, args.months, args.type, args.start, args.end)
        if not 1 <= args.port <= 65535:
            raise ValueError('端口范围为 1–65535')
        # Keep SDK logs out of machine-readable stdout, including during cleanup.
        with redirect_stdout(sys.stderr):
            with socket.create_connection((args.host, args.port), timeout=2):
                pass
            import moomoo as sdk
            signal.signal(signal.SIGINT, signal.default_int_handler)
            try:
                context = sdk.OpenQuoteContext(host=args.host, port=args.port)
                result = OptionChainService(sdk, context).query(query)
            finally:
                if context is not None:
                    context.close()
        if args.output:
            with args.output.open('w', encoding='utf-8', newline='') as stream:
                write_result(result, stream, args.format)
            print(f'已保存 {len(result["contracts"])} 个合约到 {args.output}', file=sys.stderr)
        else:
            write_result(result, sys.stdout, args.format)
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f'查询失败：{error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('查询已取消', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
