"""SubQuick — 快速字幕匹配工具入口

Usage:
    flet run main.py

首次运行会自动创建日志并触发引导向导。
"""

import sys
import time
import traceback

import flet as ft

from app.ui.app import SubQuickApp
from app.utils.logging import ensure_logging, get_logger
from app.downloader.registry import init_plugins
from app.services.settings_service import SettingsService


def main(page: ft.Page):
    # 初始化日志系统
    logger = ensure_logging()
    logger.info("SubQuick 启动")

    # 加载 plugins/ 目录中的第三方库
    init_plugins("plugins")
    logger.info("plugins 目录已加载")

    # 从设置恢复上次窗口大小
    svc = SettingsService()
    ui = svc.load().ui
    ww = ui.window_width if ui.window_width >= 800 else 1440
    wh = ui.window_height if ui.window_height >= 450 else 810
    logger.info(f"窗口大小 已保存={ui.window_width}x{ui.window_height} → 恢复={ww}x{wh}")

    # 配置窗口
    page.window.width = ww
    page.window.height = wh
    page.window.min_width = 800
    page.window.min_height = 450
    page.window.resizable = True
    page.title = "SubQuick - 快速字幕匹配工具"
    page.padding = 0
    page.spacing = 0

    # 窗口大小变更时保存（仅保存 ≥ 最小尺寸的合法值）
    _last_save = [0.0]
    def on_resize(e):
        import time
        w = page.window.width
        h = page.window.height
        if w and h and int(w) >= 800 and int(h) >= 450:
            now = time.time()
            if now - _last_save[0] < 0.3:  # 拖拽缩放最多 300ms 写一次
                return
            _last_save[0] = now
            sw, sh = int(w), int(h)
            svc2 = SettingsService()
            s = svc2.load()
            s.ui.window_width = sw
            s.ui.window_height = sh
            svc2.save(s)
            logger.info(f"窗口大小已保存: {sw}x{sh}")

    page.on_resize = on_resize

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
    try:
        ft.run(main)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
