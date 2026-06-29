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
                                content=ft.Text("验证"),
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

        # 字体选择
        font_options = [
            ft.dropdown.Option("", "默认"),
            ft.dropdown.Option("Microsoft YaHei", "微软雅黑"),
            ft.dropdown.Option("SimSun", "宋体"),
            ft.dropdown.Option("SimHei", "黑体"),
            ft.dropdown.Option("DengXian", "等线"),
            ft.dropdown.Option("KaiTi", "楷体"),
            ft.dropdown.Option("PingFang SC", "苹方"),
            ft.dropdown.Option("Noto Sans SC", "Noto Sans SC"),
        ]
        self._font_dropdown = ft.Dropdown(
            width=200,
            options=font_options,
            value=self._settings.ui.font_family,
            on_select=self._on_font_family_change,
        )

        # 字号选择
        self._font_size_dropdown = ft.Dropdown(
            width=200,
            options=[ft.dropdown.Option(str(s), f"{s}px") for s in [10, 12, 13, 14, 15, 16, 18, 20, 22, 24]],
            value=str(self._settings.ui.font_size),
            on_select=self._on_font_size_change,
        )

        ui_card = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("界面设置", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("主题模式", size=13, width=60),
                            self._theme_dropdown,
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("字体", size=13, width=60),
                            self._font_dropdown,
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("字号", size=13, width=60),
                            self._font_size_dropdown,
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

        # ── 关于 ───────────────────────────────────────

        self._update_status_text = ft.Text("", size=12, color=ft.Colors.GREY_500)

        about_card = ft.Container(
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("关于 SubQuick", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Text("快速字幕匹配工具 — 自动扫描本地视频并匹配下载字幕。", size=12),
                    ft.Text("数据来源: OpenSubtitles.org", size=12, color=ft.Colors.GREY_500),
                    ft.Row(
                        spacing=4,
                        controls=[
                            ft.Text("版本:", size=12, color=ft.Colors.GREY_500),
                            ft.Text(f"v{self._settings.version}", size=12),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        controls=[
                            ft.Text("许可:", size=12, color=ft.Colors.GREY_500),
                            ft.Text("MIT License", size=12),
                        ],
                    ),
                    ft.Divider(height=1),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Button(
                                content=ft.Text("检查更新"),
                                icon=ft.Icons.UPDATE,
                                on_click=self._check_update,
                            ),
                            self._update_status_text,
                        ],
                    ),
                    ft.Text("Copyright © 2026 SubQuick。仅供合法用途。", size=11, color=ft.Colors.GREY_400, italic=True),
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
            controls=[scan_card, ui_card, about_card],
        )

        # 可滚动的内容区（header 在外部，保持固定）
        scroll_body = ft.Column(
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Container(
                    content=ft.ResponsiveRow(
                        spacing=16,
                        columns={"sm": 12, "md": 6, "lg": 6},
                        controls=[
                            ft.Column(col={"sm": 12, "md": 6, "lg": 6}, controls=[left_column]),
                            ft.Column(col={"sm": 12, "md": 6, "lg": 6}, controls=[right_column]),
                        ],
                    ),
                    padding=ft.Padding(left=16, right=16, top=8),
                ),
            ],
        )

        super().__init__(
            spacing=0,
            expand=True,
            controls=[header, scroll_body],
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

    def _check_update(self, e=None) -> None:
        """检查 GitHub Release 更新"""
        import urllib.request
        import json
        import threading

        self._update_status_text.value = "检查中..."
        self._update_status_text.update()

        def do_check():
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/PingWangWang/SubQuick/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())

                latest_tag = data.get("tag_name", "").lstrip("v")
                current = self._settings.version

                if latest_tag and latest_tag > current:
                    msg = f"发现新版本 v{latest_tag}！当前: v{current}"
                    btn_text = "前往下载"
                    url = data.get("html_url", "")
                elif latest_tag:
                    msg = f"已是最新版本 v{current}"
                    btn_text = ""
                    url = ""
                else:
                    msg = "无法获取版本信息"
                    btn_text = ""
                    url = ""

                def update_ui():
                    self._update_status_text.value = msg
                    self._update_status_text.color = AppColors.SUCCESS if "已是最新" in msg else AppColors.INFO
                    self._update_status_text.update()
                    if url:
                        import webbrowser
                        webbrowser.open(url)

                self._app.page.run_thread(update_ui)

            except Exception as ex:
                def update_error():
                    self._update_status_text.value = f"检查失败: {ex}"
                    self._update_status_text.color = AppColors.ERROR
                    self._update_status_text.update()
                self._app.page.run_thread(update_error)

        threading.Thread(target=do_check, daemon=True).start()

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

    def _on_font_family_change(self, e):
        self._settings.ui.font_family = e.control.value
        self._app._apply_theme()
        self._save_settings()
        self._app.page.update()

    def _on_font_size_change(self, e):
        self._settings.ui.font_size = int(e.control.value)
        self._app._apply_theme()
        self._save_settings()
        self._app.page.update()

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
