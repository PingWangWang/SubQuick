"""SubQuick — 快速字幕匹配工具入口

Usage:
    flet run main.py
"""

import flet as ft
from app.ui.app import SubQuickApp


def main(page: ft.Page):
    # 必须先配置窗口，避免循环导入
    page.window_width = 1440
    page.window_height = 810
    page.window_min_width = 1280
    page.window_min_height = 720
    page.window_resizable = True
    page.title = "SubQuick - 快速字幕匹配工具"
    page.padding = 0
    page.spacing = 0

    app = SubQuickApp(page)
    app.run()


if __name__ == "__main__":
    ft.app(target=main)
