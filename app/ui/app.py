"""SubQuick Flet 应用主类与主题管理"""

from __future__ import annotations

import flet as ft

from app.services.settings_service import SettingsService
from app.ui.theme import AppColors


class SubQuickApp:
    """SubQuick 主应用，负责页面路由、主题切换和全局状态管理。"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.settings_service = SettingsService()
        self.settings = self.settings_service.load()
        self._current_page: str = "main"

    # ── 主题管理 ──────────────────────────────────────────

    def _apply_theme(self) -> None:
        """根据当前设置应用主题"""
        theme_mode = self.settings.theme
        if theme_mode == "system":
            self.page.theme_mode = ft.ThemeMode.SYSTEM
        elif theme_mode == "light":
            self.page.theme_mode = ft.ThemeMode.LIGHT
        elif theme_mode == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK

        # 自定义主题色
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        self.page.theme = ft.Theme(
            color_scheme_seed=AppColors.PRIMARY,
            use_material3=True,
        )

    def set_theme(self, theme: str) -> None:
        """切换主题模式"""
        if theme in ("system", "light", "dark"):
            self.settings.theme = theme
            self._apply_theme()
            self.settings_service.save(self.settings)
            self.page.update()

    def toggle_theme(self) -> None:
        """快速切换暗色/浅色"""
        current = self.settings.theme
        if current == "dark":
            self.set_theme("light")
        elif current == "light":
            self.set_theme("dark")
        else:
            self.set_theme("dark")

    # ── 页面路由 ──────────────────────────────────────────

    @property
    def current_page(self) -> str:
        return self._current_page

    def navigate_to(self, page_name: str) -> None:
        """切换到指定页面（使用懒导入避免循环依赖）"""
        self._current_page = page_name
        self.page.clean()

        if page_name == "main":
            from app.ui.pages.main_page import MainPage
            self.page.add(MainPage(self))
        elif page_name == "settings":
            from app.ui.pages.settings_page import SettingsPage
            self.page.add(SettingsPage(self))
        else:
            from app.ui.pages.main_page import MainPage
            self.page.add(MainPage(self))

        self.page.update()

    def run(self) -> None:
        """启动应用，加载主页面"""
        self.navigate_to("main")
