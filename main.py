"""SubQuick — 快速字幕匹配工具入口

Usage:
    flet run main.py

首次运行会自动创建日志并触发引导向导。
"""

import sys
import threading
import traceback

import flet as ft

from app.ui.app import SubQuickApp
from app.utils.logging import ensure_logging, get_logger


def _center_window_async(window_title: str, width: int, height: int) -> None:
    """等待窗口出现后将其居中（后台线程，避免闪现）"""
    import ctypes
    import ctypes.wintypes
    import time

    # 短暂等待 Flutter 窗口创建
    for _ in range(30):
        hwnd = ctypes.windll.user32.FindWindowW(None, window_title)
        if hwnd:
            screen_w = ctypes.windll.user32.GetSystemMetrics(0)
            screen_h = ctypes.windll.user32.GetSystemMetrics(1)
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2)
            # SWP_NOZORDER | SWP_NOSIZE = 0x0001 | 0x0002 = 0x0003
            # 只移动位置，不改变大小和 Z 顺序
            ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0003)
            break
        time.sleep(0.05)


def main(page: ft.Page):
    # 初始化日志系统
    logger = ensure_logging()
    logger.info("SubQuick 启动")

    # 配置窗口
    page.window_width = 1440
    page.window_height = 810
    page.window_min_width = 1280
    page.window_min_height = 720
    page.window_resizable = True
    page.title = "SubQuick - 快速字幕匹配工具"
    page.padding = 0
    page.spacing = 0

    # 注册 Flet 页面级异常处理
    def on_error(e):
        logger.error(f"页面异常: {e}", exc_info=True)
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"发生错误: {e}", size=14),
            bgcolor="#C62828",
        )
        page.snack_bar.open = True
        page.update()

    page.on_error = on_error

    try:
        app = SubQuickApp(page)
        app.run()
        logger.info("SubQuick 主界面加载完成")
    except Exception as e:
        logger.critical(f"应用启动失败: {e}", exc_info=True)
        page.clean()
        page.add(
            ft.Column(
                controls=[
                    ft.Container(height=100),
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color="#C62828"),
                    ft.Text("应用启动失败", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e), size=14, color="#757575"),
                    ft.Text("请查看日志获取详细信息", size=12, color="#9E9E9E"),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()


if __name__ == "__main__":
    # 后台线程：窗口创建后立即居中，避免先左上角再跳转的闪现
    threading.Thread(
        target=_center_window_async,
        args=("SubQuick - 快速字幕匹配工具", 1440, 810),
        daemon=True,
    ).start()

    try:
        ft.run(main)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
