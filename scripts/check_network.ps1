# scripts/check_network.ps1 — Network Connectivity Check
# Usage: .\scripts\check_network.ps1
#
# Checks if key Flet dependency servers are reachable.
# Required for Flet's first-time Flutter engine download.
# Output uses pure ASCII, compatible with any console encoding.

$ErrorActionPreference = "Stop"

Write-Host "=== SubQuick Network Connectivity Check ===" -ForegroundColor Cyan

# Activate venv if available for correct Python
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
}

# Force Python to output UTF-8 and replace non-ASCII
$env:PYTHONIOENCODING = "utf-8"

$output = python .\scripts\check_network.py 2>&1
$exitCode = $LASTEXITCODE

Write-Host $output

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "Result: All checks passed." -ForegroundColor Green
    Write-Host "Run '.\scripts\run_dev.ps1' to start the app." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Result: Some servers not reachable." -ForegroundColor Yellow
    Write-Host "" -ForegroundColor Yellow
    Write-Host "Flet downloads its desktop client from GitHub Releases:" -ForegroundColor Yellow
    Write-Host "  https://github.com/flet-dev/flet/releases/download/v0.85.3/flet-windows.zip" -ForegroundColor Gray
    Write-Host "" -ForegroundColor Yellow
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "  1. Use a proxy: `$env:HTTPS_PROXY='http://127.0.0.1:7890'`" -ForegroundColor White
    Write-Host "     then: .\scripts\run_dev.ps1" -ForegroundColor White
    Write-Host "  2. Manually download from GitHub and extract to %USERPROFILE%\.flet\client\" -ForegroundColor White
    Write-Host "  3. Set `$env:FLET_CLIENT_URL` to a custom mirror" -ForegroundColor White
}
