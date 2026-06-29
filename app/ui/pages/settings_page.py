"""设置页面 — 全屏双栏布局

配置项：
- 字幕匹配（数量、语言）
- 字幕源（API Key）
- 扫描（格式、忽略列表）
- 网络（代理）
- 界面（主题切换）
"""

from __future__ import annotations

import flet as ft
from app.ui.theme import AppColors
from app.ui.app import SubQuickApp


class SettingsPage(ft.Column):
    """设置页面 — 双栏 16:9 布局"""

    def __init__(self, app: SubQuickApp):
        self._app = app
        self._settings = app.settings

        # ── Header ─────────────────────────────────────

        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: app.navigate_to("main"),
                    ),
                    ft.Text("设置", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                ],
            ),
            padding=ft.Padding(left=8, right=16, top=8, bottom=4),
        )

        # ── 左栏控件 ───────────────────────────────────

        # 每视频匹配字幕数
        self._max_sub_slider = ft.Slider(
            min=1, max=5, divisions=4,
            value=self._settings.max_subtitles_per_video,
            label="{value}",
            width=300,
            on_change=self._on_max_sub_change,
        )
        self._max_sub_label = ft.Text(
            f"当前: {self._settings.max_subtitles_per_video} 个",
            size=13,
        )

        # 首选语言
        self._primary_lang = ft.Dropdown(
            width=200,
            options=[
                ft.dropdown.Option("zh", "简体中文"),
                ft.dropdown.Option("zh-tw", "繁体中文"),
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("ja", "日本語"),
                ft.dropdown.Option("ko", "한국어"),
                ft.dropdown.Option("fr", "Français"),
                ft.dropdown.Option("de", "Deutsch"),
                ft.dropdown.Option("es", "Español"),
            ],
            value=self._settings.language_priority.primary,
            on_select=self._on_lang_change,
        )

        # 左栏 — 字幕匹配设置
        matching_card = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("字幕匹配设置", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Text("每部视频匹配字幕数", size=13),
                    ft.Row(
                        spacing=8,
                        controls=[self._max_sub_slider, self._max_sub_label],
                    ),
                    ft.Text("首选字幕语言", size=13),
                    self._primary_lang,
                    ft.Text(
                        "未匹配到首选语言时，自动降级尝试中文 → 英文",
                        size=11,
                        color=ft.Colors.GREY_500,
                        italic=True,
                    ),
                ],
            ),
            padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
        )

        # 左栏 — 字幕源配置
        self._api_key_field = ft.TextField(
            hint_text="输入 OpenSubtitles API Key",
            value=self._settings.api_key,
            password=True,
            can_reveal_password=True,
            width=350,
            on_change=self._on_api_key_change,
        )
        provider = self._settings.subtitle_providers.get("opensubtitles")
        self._api_status = ft.Text(
            "未验证" if not (provider and provider.api_key_validated) else "有效 ✅",
            size=12,
            color=ft.Colors.GREY_500,
        )

        providers_card = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("字幕源配置", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Text("OpenSubtitles.com", size=13),
                    ft.Row(
                        spacing=8,
                        controls=[
                            self._api_key_field,
                            ft.Button(
                                "验证",
                                on_click=self._validate_api_key,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        controls=[
                            ft.Text("状态:", size=12),
                            self._api_status,
                        ],
                    ),
                    ft.TextButton(
                        "没有 Key？去 opensubtitles.com 注册",
                        url="https://www.opensubtitles.com/",
                    ),
                ],
            ),
            padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
        )

        # ── 右栏控件 ───────────────────────────────────

        # 视频格式
        self._format_checkboxes: dict[str, ft.Checkbox] = {}
        format_row = ft.Row(
            wrap=True,
            spacing=8,
            controls=[],
        )
        for fmt in ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"]:
            cb = ft.Checkbox(
                label=fmt.upper(),
                value=fmt in self._settings.video_formats,
                on_change=self._on_formats_change,
            )
            self._format_checkboxes[fmt] = cb
            format_row.controls.append(cb)

        # 忽略模式
        self._ignore_patterns = ft.TextField(
            hint_text="*sample*, *trailer*",
            value=", ".join(self._settings.ignore_list.patterns),
            width=300,
            on_change=self._on_ignore_patterns_change,
        )

        scan_card = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("扫描设置", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Text("支持扫描的视频格式:", size=13),
                    format_row,
                    ft.Text("忽略文件名模式（逗号分隔）:", size=13),
                    self._ignore_patterns,
                ],
            ),
            padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
        )

        # 界面主题
        self._theme_dropdown = ft.Dropdown(
            width=200,
            options=[
                ft.dropdown.Option("system", "跟随系统"),
                ft.dropdown.Option("light", "浅色模式"),
                ft.dropdown.Option("dark", "深色模式"),
            ],
            value=self._settings.theme,
            on_select=self._on_theme_change,
        )
        ui_card = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("界面设置", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Text("主题模式:", size=13),
                            self._theme_dropdown,
                        ],
                    ),
                ],
            ),
            padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
        )

        # 其他
        other_card = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("其他", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.TextButton(
                        "打开日志目录",
                        on_click=self._open_log_dir,
                    ),
                    ft.Text(f"版本: v{self._settings.version}", size=12, color=ft.Colors.GREY_500),
                ],
            ),
            padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
        )

        # ── 双栏布局 ───────────────────────────────────

        left_column = ft.Column(
            spacing=12,
            expand=True,
            controls=[matching_card, providers_card],
        )
        right_column = ft.Column(
            spacing=12,
            expand=True,
            controls=[scan_card, ui_card, other_card],
        )

        body = ft.Container(
            content=ft.ResponsiveRow(
                spacing=16,
                columns={"sm": 12, "md": 6, "lg": 6},
                controls=[
                    ft.Column(col={"sm": 12, "md": 6, "lg": 6}, controls=[left_column]),
                    ft.Column(col={"sm": 12, "md": 6, "lg": 6}, controls=[right_column]),
                ],
            ),
            padding=ft.Padding(left=16, right=16, top=8),
            expand=True,
        )

        super().__init__(
            spacing=0,
            expand=True,
            controls=[header, body],
        )

    # ── 回调处理 ──────────────────────────────────────────

    def _on_max_sub_change(self, e):
        value = int(e.control.value)
        self._settings.max_subtitles_per_video = value
        self._max_sub_label.value = f"当前: {value} 个"
        self._save_settings()

    def _on_lang_change(self, e):
        self._settings.language_priority.primary = e.control.value
        # 更新降级链
        from app.matcher import build_fallback_chain
        self._settings.language_priority.fallback_chain = build_fallback_chain(e.control.value)
        self._save_settings()

    def _on_api_key_change(self, e):
        self._settings.api_key = e.control.value.strip()
        self._save_settings()

    def _validate_api_key(self, e=None):
        """验证 API Key"""
        if not self._settings.api_key:
            self._api_status.value = "请输入 API Key"
            self._api_status.color = AppColors.ERROR
            self._api_status.update()
            return

        self._api_status.value = "验证中..."
        self._api_status.color = ft.Colors.GREY_500
        self._api_status.update()

        try:
            from app.downloader import OpenSubtitlesProvider
            provider = OpenSubtitlesProvider(api_key=self._settings.api_key)
            valid = provider.validate_api_key()
            if valid:
                self._api_status.value = "有效 ✅"
                self._api_status.color = AppColors.SUCCESS
                self._settings.subtitle_providers["opensubtitles"].api_key_validated = True
            else:
                self._api_status.value = "无效 ❌"
                self._api_status.color = AppColors.ERROR
                self._settings.subtitle_providers["opensubtitles"].api_key_validated = False
        except Exception as ex:
            self._api_status.value = f"验证失败: {ex}"
            self._api_status.color = AppColors.ERROR

        self._save_settings()
        self._api_status.update()

    def _on_formats_change(self, e):
        formats = [
            fmt for fmt, cb in self._format_checkboxes.items()
            if cb.value
        ]
        self._settings.video_formats = formats or ["mp4", "mkv", "avi", "mov", "wmv"]
        self._save_settings()

    def _on_ignore_patterns_change(self, e):
        patterns = [
            p.strip() for p in e.control.value.split(",")
            if p.strip()
        ]
        self._settings.ignore_list.patterns = patterns
        self._save_settings()

    def _on_theme_change(self, e):
        theme = e.control.value
        self._app.set_theme(theme)

    def _open_log_dir(self, e=None):
        """打开日志目录"""
        import os
        log_dir = os.path.join(os.environ.get("APPDATA", ""), "SubQuick", "logs")
        if os.path.exists(log_dir):
            os.startfile(log_dir)
        else:
            # 如果没有日志目录，打开配置目录
            config_dir = os.path.join(os.environ.get("APPDATA", ""), "SubQuick")
            if os.path.exists(config_dir):
                os.startfile(config_dir)

    def _save_settings(self):
        """保存设置"""
        try:
            self._app.settings_service.save(self._settings)
        except Exception:
            pass
