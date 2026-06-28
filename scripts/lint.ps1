# scripts/lint.ps1 — 代码检查
# 用法: .\scripts\lint.ps1

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "请先创建虚拟环境并安装依赖" -ForegroundColor Red
    exit 1
}

.\.venv\Scripts\Activate.ps1
pip install ruff -q
ruff check app/ main.py
