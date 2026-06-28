"""SubQuick — 快速字幕匹配工具入口

Usage:
    flet run main.py
"""

import flet as ft
from app.ui.app import SubQuickApp


def main(page: ft.Page):
    app = SubQuickApp(page)
    page.window_width = 1440
    page.window_height = 810
    page.window_min_width = 1280
    page.window_min_height = 720
    page.title = "SubQuick - 快速字幕匹配工具"
    app.run()


if __name__ == "__main__":
    ft.app(target=main)
