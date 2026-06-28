"""网络连通性检查工具

用于诊断 Flet 首次运行时下载 Flutter 引擎的网络问题。
兼容 Windows GBK 编码的控制台。
"""

import io
import subprocess
import sys
import urllib.request
import urllib.error
import ssl

# 强制 stdout/stderr 使用 UTF-8（兼容 Windows GBK 控制台）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# Flet 依赖的关键域名
CHECK_URLS = [
    ("pub.dev", "https://pub.dev/", "Dart/Flutter package repository"),
    ("github.com", "https://github.com/", "GitHub (Flet client download)"),
    ("storage.googleapis.com", "https://storage.googleapis.com/", "Flutter engine (CDN)"),
    ("pypi.org", "https://pypi.org/", "Python package index"),
]

# 使用纯 ASCII 符号代替 emoji，兼容所有编码
CHECK_MARK = "[OK]"
CROSS_MARK = "[XX]"
WARN_MARK = "[!!]"


def check_url(url: str, timeout: int = 15) -> bool:
    """检查 URL 是否可达

    先尝试 HEAD，如果失败再用 GET 重试（某些 CDN 拒绝 HEAD）。
    """
    for method in ("HEAD", "GET"):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return True
        except Exception:
            continue
    return False


def check_dns(hostname: str, timeout: int = 5) -> bool:
    """检查 DNS 解析是否正常"""
    try:
        import socket
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(hostname)
        return True
    except Exception:
        return False


def check_pip_mirror() -> str:
    """检查当前 pip 镜像源"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "config", "list"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
        for line in output.splitlines():
            if "index-url" in line.lower() or "mirror" in line.lower():
                return line.strip()
        return "default (pypi.org)"
    except Exception:
        return "unknown"


def check_proxy() -> str:
    """检查系统代理设置"""
    import os
    proxies = []
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
        val = os.environ.get(var, "")
        if val:
            proxies.append(f"{var}={val}")
    return "\n    ".join(proxies) if proxies else "none"


def run_network_check() -> list[dict]:
    """执行全面网络检查，返回结果列表"""
    results = []

    for hostname, url, desc in CHECK_URLS:
        dns_ok = check_dns(hostname)
        http_ok = check_url(url) if dns_ok else False
        results.append({
            "host": hostname,
            "description": desc,
            "dns": dns_ok,
            "http": http_ok,
        })

    return results


def print_check_results(results: list[dict]) -> None:
    """打印检查结果（纯 ASCII，兼容所有编码）"""
    all_ok = all(r["dns"] and r["http"] for r in results)

    print()
    print("=== Network Connectivity Check ===")
    print(f"Pip mirror:  {check_pip_mirror()}")
    print(f"Proxy:       {check_proxy()}")
    print()

    for r in results:
        dns_status = CHECK_MARK if r["dns"] else CROSS_MARK
        http_status = CHECK_MARK if r["http"] else CROSS_MARK
        print(f"  [{r['host']}] {r['description']}")
        print(f"    DNS: {dns_status}    HTTP: {http_status}")

    print()
    if all_ok:
        print(f"Result: {CHECK_MARK} Network is OK, Flet should work normally")
    else:
        print(f"Result: {WARN_MARK} Some servers are not reachable.")
        print()
        print("  Flet downloads its desktop client from GitHub Releases:")
        print("    https://github.com/flet-dev/flet/releases/download/v{ver}/flet-windows.zip")
        print("  This is a one-time download cached at %USERPROFILE%\\.flet\\client\\")
        print()
        print("  Solutions:")
        print("  [1] Use a proxy:")
        print("      $env:HTTPS_PROXY='http://127.0.0.1:7890'")
        print("      .\\scripts\\run_dev.ps1")
        print()
        print("  [2] Manually pre-seed the cache:")
        print("      On a machine with good network, download:")
        print("      https://github.com/flet-dev/flet/releases/download/v0.85.3/flet-windows.zip")
        print("      Then extract to: %USERPROFILE%\\.flet\\client\\flet\\")
        print()
        print("  [3] Set a custom download URL via environment variable:")
        print("      $env:FLET_CLIENT_URL='https://your-mirror/flet-windows.zip'")
        print("      .\\scripts\\run_dev.ps1")


if __name__ == "__main__":
    results = run_network_check()
    print_check_results(results)
    sys.exit(0 if all(r["dns"] and r["http"] for r in results) else 1)
