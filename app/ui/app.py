"""SubQuick Flet 应用主类"""

import flet as ft


class SubQuickApp:
    """SubQuick 主应用，负责页面路由和全局状态管理。"""

    def __init__(self, page: ft.Page):
        self.page = page

    def run(self):
        """启动应用，加载主页面。"""
        from app.ui.pages.main_page import MainPage
        self.page.clean()
        self.page.add(MainPage(self.page))
        self.page.update()
