param([switch]$Desktop, [switch]$Help)
$ErrorActionPreference = 'Stop'
if ($Help) {
    Write-Output 'Usage: .\setup.ps1 [-Desktop]'
    Write-Output 'Install CLI + MCP; optionally add the desktop UI. Requires uv.'
    exit 0
}
$MoomooPython = Join-Path $PSScriptRoot 'apps\python\.venv\Scripts\python.exe'
$MoomooEnvironment = Join-Path $PSScriptRoot 'apps\python\.venv'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv first: winget install --id=astral-sh.uv -e'
}
if (Test-Path -LiteralPath $MoomooEnvironment) {
    if (-not (Test-Path -LiteralPath $MoomooPython)) {
        throw 'Existing .venv is incomplete; it has been preserved. Check it before reinstalling.'
    }
    & $MoomooPython -c 'import sys; raise SystemExit(sys.version_info[:2] != (3,14))'
    if ($LASTEXITCODE -ne 0) { throw 'Existing .venv is not Python 3.14; it has been preserved.' }
} else {
    Write-Output 'Preparing Python 3.14 (uv downloads it when needed)...'
    & uv venv --python 3.14 $MoomooEnvironment
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
function Install-MoomooDependency {
    param([string[]]$UvArguments)
    # Expected cache misses must not become terminating native errors in Windows PowerShell.
    $MoomooPreviousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & uv --offline pip install @UvArguments *> $null
        $MoomooCacheExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $MoomooPreviousPreference }
    if ($MoomooCacheExit -ne 0) {
        Write-Output 'Downloading missing dependencies...'
        & uv --system-certs pip install @UvArguments
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
Write-Output 'Installing project dependencies...'
Install-MoomooDependency -UvArguments @('--python', $MoomooPython, 'setuptools>=77')
$MoomooExtras = if ($Desktop) { 'mcp,desktop' } else { 'mcp' }
$MoomooProject = (Join-Path $PSScriptRoot 'apps\python') + '[' + $MoomooExtras + ']'
Install-MoomooDependency -UvArguments @('--python', $MoomooPython, '--no-build-isolation', '-e', $MoomooProject)
& $MoomooPython -X utf8 -c "import importlib.metadata as m; print(', '.join(n + ' ' + m.version(n) for n in ('moomoo-clients','moomoo-api','mcp')))"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output 'Installation complete. Sign into official OpenD, then run .\moomoo.ps1 doctor.'
Write-Output 'OpenD download: https://www.moomoo.com/download/OpenAPI'
