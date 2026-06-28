# scripts/run_dev.ps1 — 开发运行
# 用法: .\scripts\run_dev.ps1

$ErrorActionPreference = "Stop"

# 检查虚拟环境
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "虚拟环境不存在，正在创建..." -ForegroundColor Yellow
    python -m venv .venv
}

# 激活虚拟环境并运行
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
flet run main.py --port 8550
