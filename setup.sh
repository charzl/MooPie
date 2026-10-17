#!/usr/bin/env bash
set -euo pipefail

MOOMOO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
MOOMOO_PYTHON="$MOOMOO_ROOT/apps/python/.venv/bin/python"
MOOMOO_EXTRAS=mcp
case "${1:-}" in
  '') ;;
  --desktop) MOOMOO_EXTRAS=mcp,desktop ;;
  -h|--help)
    echo '用法：./setup.sh [--desktop]'
    echo '默认安装行情 CLI + MCP；--desktop 另安装桌面界面。需要 uv。'
    exit 0 ;;
  *) echo '未知参数；用法：./setup.sh [--desktop]' >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
  echo '用法：./setup.sh [--desktop]' >&2
  exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
  echo '请先安装 uv：brew install uv（其他平台：https://docs.astral.sh/uv/getting-started/installation/）' >&2
  exit 1
fi
if [ -e "$MOOMOO_ROOT/apps/python/.venv" ]; then
  if [ ! -x "$MOOMOO_PYTHON" ] || ! "$MOOMOO_PYTHON" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3,14))'; then
    echo '现有 apps/python/.venv 不是可用的 Python 3.14 环境；已保留，请先检查。' >&2
    exit 1
  fi
else
  echo '正在准备 Python 3.14 环境；缺少解释器时 uv 会下载。'
  uv venv --python 3.14 "$MOOMOO_ROOT/apps/python/.venv"
fi
echo '正在安装项目和依赖……'
# Reuse the local build backend on reinstall instead of fetching an isolated copy.
if ! uv --offline pip install --python "$MOOMOO_PYTHON" 'setuptools>=77' >/dev/null 2>&1; then
  uv --system-certs pip install --python "$MOOMOO_PYTHON" 'setuptools>=77'
fi
if ! uv --offline pip install --python "$MOOMOO_PYTHON" --no-build-isolation -e "$MOOMOO_ROOT/apps/python[$MOOMOO_EXTRAS]" >/dev/null 2>&1; then
  echo '本地缓存不足，正在联网安装所需依赖……'
  uv --system-certs pip install --python "$MOOMOO_PYTHON" --no-build-isolation -e "$MOOMOO_ROOT/apps/python[$MOOMOO_EXTRAS]"
fi
"$MOOMOO_PYTHON" -c 'import importlib.metadata as m; print("安装完成：" + ", ".join(n + " " + m.version(n) for n in ("moomoo-clients","moomoo-api","mcp")))'
echo '下一步：在官方 OpenD 窗口登录，然后运行 ./moomoo doctor。'
echo 'OpenD 下载：https://www.moomoo.com/download/OpenAPI'
