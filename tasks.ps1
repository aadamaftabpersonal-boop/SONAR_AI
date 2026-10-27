# Windows task runner mirroring the Makefile (make is not installed here).
# Usage: .\tasks.ps1 <task>     e.g.  .\tasks.ps1 setup | check | run | db-up
param([Parameter(Position = 0)][string]$Task = "help")

$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Venv = Join-Path $Backend ".venv"
$Py = Join-Path $Venv "Scripts\python.exe"

function Run($exe, $argList, $dir = $Root) {
    Push-Location $dir
    try { & $exe @argList; if ($LASTEXITCODE -ne 0) { throw "failed: $exe $argList" } }
    finally { Pop-Location }
}

switch ($Task) {
    "setup" {
        if (-not (Test-Path $Py)) { Run "py" @("-3", "-m", "venv", $Venv) }
        Run $Py @("-m", "pip", "install", "--upgrade", "pip")
        Run $Py @("-m", "pip", "install", "-e", ".[dev]") $Backend
    }
    "doctor" {
        Run "python" @("--version"); Run "node" @("--version"); Run "docker" @("--version"); Run "git" @("--version")
        if (Test-Path $Py) { Run $Py @("--version") } else { Write-Host "no venv yet: run setup" }
    }
    "db-up" { Run "docker" @("compose", "up", "-d", "--wait", "db") }
    "db-down" { Run "docker" @("compose", "down") }
    "run" { Run $Py @("-m", "uvicorn", "app.main:app", "--reload", "--port", "8000") $Backend }
    "test" { Run $Py @("-m", "pytest") $Backend }
    "test-int" { Run $Py @("-m", "pytest", "-m", "integration") $Backend }
    "lint" {
        Run $Py @("-m", "ruff", "check", ".") $Backend
        Run $Py @("-m", "ruff", "format", "--check", ".") $Backend
    }
    "fmt" {
        Run $Py @("-m", "ruff", "check", "--fix", ".") $Backend
        Run $Py @("-m", "ruff", "format", ".") $Backend
    }
    "secrets" { Run $Py @("scripts/check_no_secrets.py") }
    "claims" { Run $Py @("scripts/check_claims.py") }
    "check-bundle" {
        Run "npm" @("--prefix", "frontend", "run", "build")
        Run $Py @("scripts/check_bundle.py")
    }
    "check-wave2" {
        $flags = "FEATURE_STOP_RULE","FEATURE_HISTORY","FEATURE_DIGEST","FEATURE_LIVE_TICKER","FEATURE_VOICE_UI","FEATURE_DISCOVERY","FEATURE_OPT_IN"
        foreach ($f in $flags) { Set-Item "env:$f" "true" }
        try { Run $Py @("-m", "pytest") $Backend } finally { foreach ($f in $flags) { Remove-Item "env:$f" } }
    }
    "e2e" { Run "npm" @("--prefix", "e2e", "test") }
    "check" {
        & $PSCommandPath lint; & $PSCommandPath test; & $PSCommandPath secrets
        & $PSCommandPath claims
    }
    default { Write-Host "tasks: setup doctor db-up db-down run test test-int lint fmt secrets claims check-bundle check check-wave2 e2e" }
}
