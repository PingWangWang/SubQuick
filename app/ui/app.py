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
        self._main_page = None
        self._settings_page = None

    # ── 主题管理 ──────────────────────────────────────────

    def _apply_theme(self) -> None:
        """根据当前设置应用主题（启动时和切换时均需调用）"""
        theme_mode = self.settings.theme
        if theme_mode == "system":
            self.page.theme_mode = ft.ThemeMode.SYSTEM
        elif theme_mode == "light":
            self.page.theme_mode = ft.ThemeMode.LIGHT
        elif theme_mode == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK

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
        """切换到指定页面（缓存页面实例，避免重复创建丢失状态）"""
        self._current_page = page_name
        self.page.clean()

        if page_name == "main":
            if self._main_page is None:
                from app.ui.pages.main_page import MainPage
                self._main_page = MainPage(self)
            self.page.add(self._main_page)
        elif page_name == "settings":
            from app.ui.pages.settings_page import SettingsPage
            self._settings_page = SettingsPage(self)
            self.page.add(self._settings_page)
        else:
            if self._main_page is None:
                from app.ui.pages.main_page import MainPage
                self._main_page = MainPage(self)
            self.page.add(self._main_page)

        self.page.update()

    def run(self) -> None:
        """启动应用

        首次运行显示引导向导，否则直接进入主界面。
        """
        # 先应用已保存的主题
        self._apply_theme()

        if self.settings.first_run:
            from app.ui.pages.wizard_page import WizardPage
            self.page.clean()
            self.page.add(WizardPage(self))
            self.page.update()
        else:
            self.navigate_to("main")
