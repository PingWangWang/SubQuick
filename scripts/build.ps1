# scripts/build.ps1 — PyInstaller 打包
# 用法: .\scripts\build.ps1

$ErrorActionPreference = "Stop"

# 检查虚拟环境
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "虚拟环境不存在，请先运行 .\scripts\run_dev.ps1" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境并打包
.\.venv\Scripts\Activate.ps1
pip install pyinstaller -q
pyinstaller build.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host "打包完成: dist/SubQuick/" -ForegroundColor Green
} else {
    Write-Host "打包失败，请检查错误信息" -ForegroundColor Red
}
