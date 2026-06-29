"""首次运行引导页面

三步引导向导：
Step 1: 欢迎 + 免责声明
Step 2: 配置 OpenSubtitles API Key
Step 3: 选择语言 + 匹配数量
完成后进入主界面。
"""

from __future__ import annotations

import flet as ft
from app.ui.theme import AppColors
from app.ui.app import SubQuickApp
from app.matcher import build_fallback_chain


class WizardPage(ft.Column):
    """首次运行引导页面 — 三步向导"""

    def __init__(self, app: SubQuickApp):
        self._app = app
        self._step = 1
        self._total_steps = 4  # 欢迎 + API Key + 语言 + 完成

        # ── Step 控件的引用 ──────────────────────────
        self._step_container = ft.Container(expand=True)
        self._step_indicator = ft.Text("步骤 1/4", size=12, color=ft.Colors.GREY_500)
        self._back_btn = ft.TextButton("上一步", disabled=True, on_click=self._go_back)
        self._next_btn = ft.Button("下一步", on_click=self._go_next)
        self._skip_btn = ft.TextButton("跳过引导", on_click=self._finish_wizard)

        # 各步骤中收集的数据
        self._api_key = ""
        self._primary_lang = "zh"
        self._max_subtitles = 3

        # ── 标题 ────────────────────────────────────
        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ROCKET_LAUNCH, size=32, color=AppColors.PRIMARY),
                    ft.Text("欢迎使用 SubQuick", size=28, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding(top=60, bottom=20),
        )

        # ── 底部导航 ─────────────────────────────────
        footer = ft.Container(
            content=ft.Row(
                controls=[
                    self._skip_btn,
                    ft.Container(expand=True),
                    self._back_btn,
                    self._next_btn,
                ],
            ),
            padding=ft.Padding(left=40, right=40, top=10, bottom=30),
        )

        # ── 布局 ────────────────────────────────────
        super().__init__(
            spacing=0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                header,
                self._step_indicator,
                ft.Divider(height=1),
                self._step_container,
                ft.Divider(height=1),
                footer,
            ],
        )

        # 加载第一步（在 did_mount 中执行，确保控件已挂载到页面）
        # self._show_step(1) 移至 did_mount

    # ── 生命周期 ─────────────────────────────────────────

    def did_mount(self):
        """控件添加到页面后，加载第一步内容"""
        self._show_step(1)

    def _show_step(self, step: int) -> None:
        """显示指定步骤的内容"""
        self._step = step
        self._step_indicator.value = f"步骤 {step}/{self._total_steps}"

        if step == 1:
            self._step_container.content = self._build_step1_welcome()
        elif step == 2:
            self._step_container.content = self._build_step2_api_key()
        elif step == 3:
            self._step_container.content = self._build_step3_language()
        elif step == 4:
            self._step_container.content = self._build_step4_complete()

        # 更新按钮状态
        self._back_btn.disabled = step <= 1
        if step >= self._total_steps:
            self._next_btn.text = "开始使用"
        else:
            self._next_btn.text = "下一步"
        self._skip_btn.visible = step < self._total_steps - 1

        self._step_container.update()
        self._step_indicator.update()
        self._back_btn.update()
        self._next_btn.update()
        self._skip_btn.update()

    def _build_step1_welcome(self) -> ft.Container:
        """Step 1: 欢迎 + 免责声明"""
        return ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(height=20),
                    ft.Text(
                        "快速字幕匹配工具",
                        size=18,
                        color=ft.Colors.GREY_600,
                    ),
                    ft.Container(
                        content=ft.Column(
                            spacing=12,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.Icons.SEARCH, color=AppColors.PRIMARY),
                                        ft.Text("批量扫描本地视频", size=14),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.Icons.DOWNLOAD, color=AppColors.PRIMARY),
                                        ft.Text("自动检测缺失字幕", size=14),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.Icons.LANGUAGE, color=AppColors.PRIMARY),
                                        ft.Text("一键在线匹配下载", size=14),
                                    ],
                                ),
                            ],
                        ),
                        padding=20,
                    ),
                    ft.Divider(height=1),
                    ft.Container(
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(
                                    "免责声明",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.WARNING,
                                ),
                                ft.Text(
                                    "SubQuick 仅提供技术工具，不托管、不存储任何字幕文件。"
                                    "所有字幕内容来自第三方 API，版权归原作者所有。"
                                    "请仅将本工具用于合法目的。",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                        ),
                        padding=12,
                        bgcolor=ft.Colors.with_opacity(0.05, AppColors.WARNING),
                        border_radius=8,
                        width=500,
                    ),
                ],
            ),
            padding=40,
        )

    def _build_step2_api_key(self) -> ft.Container:
        """Step 2: 配置 OpenSubtitles API Key"""
        key_field = ft.TextField(
            hint_text="输入您的 OpenSubtitles API Key",
            value=self._api_key,
            password=True,
            can_reveal_password=True,
            width=400,
            on_change=lambda e: setattr(self, '_api_key', e.control.value.strip()),
        )
        status_text = ft.Text("", size=12)

        def validate_key(e=None):
            key = key_field.value.strip()
            if not key:
                status_text.value = "请输入 API Key"
                status_text.color = AppColors.WARNING
                status_text.update()
                return
            self._api_key = key
            status_text.value = "验证中..."
            status_text.color = ft.Colors.GREY_500
            status_text.update()

            try:
                from app.downloader import OpenSubtitlesProvider
                provider = OpenSubtitlesProvider(api_key=key)
                valid = provider.validate_api_key()
                if valid:
                    status_text.value = "验证通过 ✅"
                    status_text.color = AppColors.SUCCESS
                    self._app.settings.api_key = key
                    self._app.settings.subtitle_providers["opensubtitles"].api_key_validated = True
                else:
                    status_text.value = "无效的 API Key ❌ 请检查后重试"
                    status_text.color = AppColors.ERROR
            except Exception as ex:
                status_text.value = f"验证失败: {ex}"
                status_text.color = AppColors.ERROR
            status_text.update()

        return ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(height=20),
                    ft.Text("配置字幕源", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "SubQuick 使用 OpenSubtitles.com 搜索和下载字幕，"
                        "需要 API Key 才能正常工作。",
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                        width=500,
                    ),
                    ft.Container(height=10),
                    ft.Text("OpenSubtitles API Key", size=14),
                    key_field,
                    ft.Button("验证 Key", on_click=validate_key),
                    status_text,
                    ft.TextButton(
                        "没有 Key？前往 opensubtitles.com 注册",
                        url="https://www.opensubtitles.com/",
                    ),
                ],
            ),
            padding=40,
        )

    def _build_step3_language(self) -> ft.Container:
        """Step 3: 选择语言和匹配数量"""
        lang_dropdown = ft.Dropdown(
            width=250,
            options=[
                ft.dropdown.Option("zh", "简体中文"),
                ft.dropdown.Option("zh-tw", "繁体中文"),
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("ja", "日本語"),
                ft.dropdown.Option("ko", "한국어"),
            ],
            value=self._primary_lang,
            on_select=lambda e: setattr(self, '_primary_lang', e.control.value),
        )
        max_sub_slider = ft.Slider(
            min=1, max=5, divisions=4,
            value=self._max_subtitles,
            label="{value}",
            width=300,
            on_change=lambda e: setattr(self, '_max_subtitles', int(e.control.value)),
        )
        max_sub_label = ft.Text(f"每视频匹配 {self._max_subtitles} 个字幕")

        def update_label(e):
            self._max_subtitles = int(e.control.value)
            max_sub_label.value = f"每视频匹配 {self._max_subtitles} 个字幕"
            max_sub_label.update()

        max_sub_slider.on_change = update_label

        return ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(height=20),
                    ft.Text("偏好设置", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    ft.Text("首选字幕语言", size=14),
                    lang_dropdown,
                    ft.Text(
                        "未匹配到首选语言时，自动降级尝试中文 → 英文",
                        size=12,
                        color=ft.Colors.GREY_500,
                    ),
                    ft.Container(height=10),
                    ft.Text("每部视频匹配字幕数", size=14),
                    max_sub_slider,
                    max_sub_label,
                ],
            ),
            padding=40,
        )

    def _build_step4_complete(self) -> ft.Container:
        """Step 4: 完成引导"""
        return ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(height=40),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=64, color=AppColors.SUCCESS),
                    ft.Text("设置完成!", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "现在可以开始使用了。\n选择一个视频目录，点击「开始扫描」即可。",
                        size=14,
                        color=ft.Colors.GREY_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text("配置摘要:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text(f"API Key: {'✓ 已配置' if self._api_key else '✗ 跳过'}", size=12),
                                ft.Text(f"首选语言: {self._primary_lang}", size=12),
                                ft.Text(f"匹配数量: {self._max_subtitles}", size=12),
                            ],
                        ),
                        padding=16,
                        bgcolor=ft.Colors.with_opacity(0.05, AppColors.PRIMARY),
                        border_radius=8,
                    ),
                ],
            ),
            padding=40,
        )

    # ── 导航 ──────────────────────────────────────────

    def _go_next(self, e=None) -> None:
        """下一步"""
        if self._step < self._total_steps:
            if self._step == 2:
                # Step 2 完成时保存 API Key
                if self._api_key:
                    self._app.settings.api_key = self._api_key

            if self._step == self._total_steps - 1:
                # 最后一步，保存所有设置并完成
                self._save_settings()
                self._finish_wizard()
                return

            self._show_step(self._step + 1)

    def _go_back(self, e=None) -> None:
        """上一步"""
        if self._step > 1:
            self._show_step(self._step - 1)

    def _save_settings(self) -> None:
        """保存引导中配置的设置"""
        self._app.settings.max_subtitles_per_video = self._max_subtitles
        self._app.settings.language_priority.primary = self._primary_lang
        self._app.settings.language_priority.fallback_chain = build_fallback_chain(self._primary_lang)
        self._app.settings.first_run = False
        try:
            self._app.settings_service.save(self._app.settings)
        except Exception:
            pass

    def _finish_wizard(self, e=None) -> None:
        """完成引导，进入主界面"""
        self._app.settings.first_run = False
        try:
            self._app.settings_service.save(self._app.settings)
        except Exception:
            pass
        self._app.navigate_to("main")
