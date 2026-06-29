# scripts/run_dev.ps1 — 开发调试启动
# 用法: .\scripts\run_dev.ps1
#
# 首次运行时会下载 Flutter 引擎（约 50-200MB，1-5 分钟，一次性）。
# 自动检查网络连通性和 Flet 缓存状态，避免无进度卡住。

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    SubQuick 开发调试启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: 虚拟环境 ──────────────────────────────────
Write-Host "[1/5] 检查虚拟环境..." -ForegroundColor Yellow
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "  → 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "  ✅ 虚拟环境已存在" -ForegroundColor Green
}

.\.venv\Scripts\Activate.ps1
Write-Host "  ✅ 虚拟环境已激活" -ForegroundColor Green
Write-Host ""

# ── Step 2: 网络检查 ──────────────────────────────────
Write-Host "[2/5] 检查网络连通性..." -ForegroundColor Yellow
try {
    $result = python .\scripts\check_network.py 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-Host "  ✅ 网络连接正常" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ 网络检查异常，请排查代理/VPN/防火墙设置" -ForegroundColor Yellow
        Write-Host "  $result" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠ 网络检查跳过（脚本异常）" -ForegroundColor Yellow
}
Write-Host ""

# ── Step 3: 安装依赖 ──────────────────────────────────
Write-Host "[3/5] 安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt -q
Write-Host "  ✅ 依赖安装完成" -ForegroundColor Green
Write-Host ""

# ── Step 4: 检查 Flet 缓存 ────────────────────────────
Write-Host "[4/5] 检查 Flet 运行环境..." -ForegroundColor Yellow

$fletCache = "$env:LOCALAPPDATA\flet"
$fletCacheHome = "$env:USERPROFILE\.flet"
$fletClientDir = "$env:USERPROFILE\.flet\client"
$localFletZip = ".\plugins\flet\flet-windows.zip"
$cacheReady = $false

if (Test-Path $fletCache) {
    $size = (Get-ChildItem -Recurse $fletCache | Measure-Object -Property Length -Sum).Sum
    if ($size -gt 10MB) {
        $cacheReady = $true
        Write-Host "  ✅ Flet 引擎缓存已就绪 ($([math]::Round($size/1MB)) MB)" -ForegroundColor Green
    }
}
if (-not $cacheReady -and (Test-Path $fletCacheHome)) {
    $size = (Get-ChildItem -Recurse $fletCacheHome | Measure-Object -Property Length -Sum).Sum
    if ($size -gt 10MB) {
        $cacheReady = $true
        Write-Host "  ✅ Flet 引擎缓存已就绪 ($([math]::Round($size/1MB)) MB)" -ForegroundColor Green
    }
}

# 如果缓存未就绪，检测本地预下载的 zip
if (-not $cacheReady -and (Test-Path $localFletZip)) {
    Write-Host "  📦 检测到本地预下载的 Flet 引擎包" -ForegroundColor Cyan
    Write-Host "  → 正在解压到 Flet 缓存目录 ..." -ForegroundColor Yellow

    # 确保目标目录存在
    New-Item -ItemType Directory -Force -Path $fletClientDir | Out-Null

    # 解压 zip（需要 .NET 的 ZipFile 或 PowerShell 5+ 的 Expand-Archive）
    try {
        # 先清空旧缓存避免残留冲突
        if (Test-Path "$fletClientDir\*") {
            Remove-Item -Recurse -Force "$fletClientDir\*"
        }
        Expand-Archive -Path $localFletZip -DestinationPath $fletClientDir -Force
        $size = (Get-ChildItem -Recurse $fletClientDir | Measure-Object -Property Length -Sum).Sum
        Write-Host "  ✅ Flet 引擎缓存已就绪（来自本地包，$([math]::Round($size/1MB)) MB）" -ForegroundColor Green
        $cacheReady = $true
    } catch {
        Write-Host "  ⚠ 解压失败: $_" -ForegroundColor Red
        Write-Host "  → 将尝试自动从网络下载" -ForegroundColor Yellow
    }
}

if (-not $cacheReady) {
    Write-Host "  ⏳ Flet 引擎尚未下载（首次运行需要）" -ForegroundColor Yellow
    Write-Host "  " -NoNewline
    Write-Host "将要下载 Flutter 引擎（约 50-200MB），在此期间没有进度条是正常的。" -ForegroundColor Cyan
    Write-Host "  " -NoNewline
    Write-Host "可以通过任务管理器查看网络流量确认下载正在进行。" -ForegroundColor Cyan
}
Write-Host ""

# ── Step 5: 启动应用 ──────────────────────────────────
Write-Host "[5/5] 启动 SubQuick..." -ForegroundColor Yellow
Write-Host "  端口: http://localhost:8550" -ForegroundColor Gray
Write-Host "  按 Ctrl+C 停止" -ForegroundColor Gray
Write-Host ""

flet run main.py --port 8550
