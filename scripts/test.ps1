# scripts/test.ps1 — 运行测试
# 用法: .\scripts\test.ps1

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "请先创建虚拟环境并安装依赖" -ForegroundColor Red
    exit 1
}

.\.venv\Scripts\Activate.ps1
pip install pytest -q
pytest tests/ -v
