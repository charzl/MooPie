"""Explain installation / gateway failures with one small, read-only quote call."""
import argparse
from contextlib import redirect_stdout
from importlib.metadata import PackageNotFoundError, version
import math
import sys

from .market_collection import opend_connection
from .options import option_symbol


def check(port=11111, symbol='AAPL', connection=opend_connection):
    if sys.version_info[:2] != (3, 14):
        print('Python：需要 3.14，请用 ./setup.sh 准备项目环境。')
        return 1
    print('Python：' + sys.version.split()[0])
    for name in ('moomoo-clients', 'moomoo-api', 'mcp'):
        try:
            print(name + '：' + version(name))
        except PackageNotFoundError:
            print(name + '：未安装，请重新运行 ./setup.sh。')
            return 1
    try:
        code = option_symbol(symbol)
        if not code.startswith('US.') or not 1 <= port <= 65535:
            raise ValueError('doctor 使用 US 标的，端口范围为 1–65535')
        with redirect_stdout(sys.stderr):
            with connection(port=port) as service:
                result = service.snapshots([code])
        row = next((r for r in result['rows'] if r.get('code') == code), None)
        if row is None or result.get('missing_codes'):
            raise ValueError('OpenD 没有返回请求标的的报价，请检查对应行情权限')
        price = row.get('last_price')
        if isinstance(price, bool) or not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 0:
            raise ValueError('OpenD 返回的报价不可用，请检查登录和行情权限')
        print(f'OpenD：127.0.0.1:{port} 已连接，真实行情请求成功')
        print(f'{code}：{price}，broker 更新时间：{row.get("update_time", "未提供")}')
        print('可使用 CLI 和 MCP 服务；agent 宿主还需单独注册并发现 MCP 工具。')
        print('收盘后可能返回最近交易时段的报价，更新时间不保证 Bid 可成交。')
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print('检查未通过：' + str(error))
        print('请启动官方 OpenD、完成登录，核对本机 API 端口和数据权限，再重试。')
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description='检查项目安装和一次只读 OpenD 行情请求')
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--symbol', default='AAPL', help='用于验证的美股代码，默认 AAPL')
    args = parser.parse_args(argv)
    return check(args.port, args.symbol)


if __name__ == '__main__': raise SystemExit(main())
