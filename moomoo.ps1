$ErrorActionPreference = 'Stop'
$MoomooCommand = if ($args.Count -gt 0) { [string]$args[0] } else { 'help' }
$MoomooTail = @()
if ($args.Count -gt 1) { $MoomooTail = @($args[1..($args.Count - 1)]) }
if ($MoomooCommand -in @('help', '--help', '-h')) {
    Write-Output @'
Usage: .\moomoo.ps1 <command> [arguments]
  doctor    Check installation, OpenD and one real stock quote
  options   Query option expirations, strikes and contract codes
  collect   Save option quotes, daily bars and earnings as JSON
  db        Inspect SQLite, configure retention and clean old snapshots
  watchlist Precheck JSON stock list, then research every stock
  paper     Virtual equity clients, strategy comparison and backtests
  analyze   Analyze saved JSON with the independent rule file
  mcp       Start the read-only MCP stdio server
  desktop   Open optional UI (install with .\setup.ps1 -Desktop)
First installation: .\setup.ps1
'@
    exit 0
}
if ($MoomooCommand -notin @('doctor', 'options', 'collect', 'analyze', 'mcp', 'desktop', 'db', 'watchlist', 'paper')) {
    Write-Error "Unknown command: $MoomooCommand. Run .\moomoo.ps1 --help." -ErrorAction Continue
    exit 2
}
$MoomooPython = Join-Path $PSScriptRoot 'apps\python\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $MoomooPython)) {
    Write-Error 'Run .\setup.ps1 first.'
    exit 1
}
switch ($MoomooCommand) {
    doctor { & $MoomooPython -X utf8 -m moopython.doctor @MoomooTail }
    options { & $MoomooPython -X utf8 -m moopython.options_cli @MoomooTail }
    collect { & $MoomooPython -X utf8 -m moopython.market_data_cli @MoomooTail }
    db { & $MoomooPython -X utf8 -m moopython.database_cli @MoomooTail }
    watchlist { & $MoomooPython -X utf8 -m moopython.watchlist_cli @MoomooTail }
    paper { & $MoomooPython -X utf8 -m moopython.paper_cli @MoomooTail }
    analyze { & $MoomooPython -X utf8 (Join-Path $PSScriptRoot 'modules\put-screener\put_rules.py') @MoomooTail }
    mcp { & $MoomooPython -X utf8 -m moopython.market_mcp @MoomooTail }
    desktop {
        & $MoomooPython -c "import importlib.util,sys; sys.exit(importlib.util.find_spec('PySide6') is None)"
        if ($LASTEXITCODE -ne 0) { throw 'Install the UI with .\setup.ps1 -Desktop first.' }
        & $MoomooPython -X utf8 (Join-Path $PSScriptRoot 'apps\python\main.py') @MoomooTail
    }
}
exit $LASTEXITCODE
