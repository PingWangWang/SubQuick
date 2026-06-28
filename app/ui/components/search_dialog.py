"""手动搜索对话框组件

提供用户手动搜索字幕的功能，搜索结果显示在列表中供用户选择下载。
"""

from __future__ import annotations

import flet as ft
from typing import Optional, Callable

from app.ui.theme import AppColors
from app.ui.components.status_badge import StatusBadge
from app.downloader.base import SearchParams


class SearchDialog(ft.AlertDialog):
    """手动搜索字幕对话框"""

    def __init__(
        self,
        page: ft.Page,
        video_name: str = "",
        video_path: str = "",
        on_search: Optional[Callable] = None,
        on_download: Optional[Callable] = None,
    ):
        self._page = page
        self._video_name = video_name
        self._video_path = video_path
        self._on_search = on_search
        self._on_download = on_download

        # 搜索输入
        self._query_field = ft.TextField(
            hint_text="输入电影名或关键词",
            value=video_name,
            width=300,
            on_submit=self._do_search,
        )
        self._imdb_field = ft.TextField(
            hint_text="IMDb ID (可选)",
            width=200,
        )
        self._search_btn = ft.ElevatedButton(
            "搜索",
            icon=ft.Icons.SEARCH,
            on_click=self._do_search,
        )

        # 搜索状态
        self._status_text = ft.Text("", size=12, color=ft.Colors.GREY_600)

        # 结果列表区域
        self._results_column = ft.Column(
            spacing=4,
            height=300,
            scroll=ft.ScrollMode.AUTO,
            visible=False,
        )

        # 下载按钮
        self._download_btn = ft.ElevatedButton(
            "下载选中",
            icon=ft.Icons.DOWNLOAD,
            disabled=True,
            on_click=self._do_download,
        )
        self._cancel_btn = ft.TextButton("取消", on_click=self._close)

        super().__init__(
            title=ft.Text(f"手动搜索字幕 - {video_name}" if video_name else "手动搜索字幕"),
            content=ft.Column(
                width=580,
                height=450,
                spacing=12,
                controls=[
                    # 视频信息
                    ft.Text(f"视频: {video_name}", size=12, color=ft.Colors.GREY_600) if video_name else ft.Container(),
                    ft.Text(f"路径: {video_path}", size=11, color=ft.Colors.GREY_500) if video_path else ft.Container(),
                    ft.Divider(height=1),

                    # 搜索输入区
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self._query_field,
                            self._imdb_field,
                            self._search_btn,
                        ],
                    ),
                    self._status_text,

                    # 结果列表
                    ft.Container(
                        content=self._results_column,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=8,
                        padding=8,
                        expand=True,
                    ),
                ],
            ),
            actions=[
                self._download_btn,
                self._cancel_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _do_search(self, e=None) -> None:
        """执行搜索"""
        query = self._query_field.value.strip()
        if not query:
            self._status_text.value = "请输入搜索关键词"
            self._status_text.color = AppColors.WARNING
            self.update()
            return

        self._status_text.value = "正在搜索..."
        self._status_text.color = ft.Colors.GREY_600
        self._search_btn.disabled = True
        self.update()

        if self._on_search:
            params = SearchParams(
                query=query,
                file_name=self._video_name,
                imdb_id=self._imdb_field.value.strip(),
            )
            # 回调处理搜索结果
            self._on_search(params)

    def show_results(self, results: list[dict]) -> None:
        """显示搜索结果

        Args:
            results: 搜索结果列表
        """
        self._results_column.controls.clear()
        self._search_btn.disabled = False

        if not results:
            self._status_text.value = "未找到匹配的字幕"
            self._status_text.color = AppColors.WARNING
            self._results_column.visible = False
            self.update()
            return

        # 创建结果列表
        for idx, item in enumerate(results):
            lang = item.get("language_display", item.get("language", "未知"))
            score = item.get("score", 0)
            file_name = item.get("file_name", "")
            row = ft.Checkbox(
                label=f"[{lang}] {file_name}  (评分: {score})",
                value=False,
                data=item,
                on_change=self._on_selection_change,
            )
            self._results_column.controls.append(row)

        self._status_text.value = f"找到 {len(results)} 个字幕，请选择要下载的"
        self._status_text.color = AppColors.SUCCESS
        self._results_column.visible = True
        self._download_btn.disabled = True
        self.update()

    def _on_selection_change(self, e) -> None:
        """选择变化时更新下载按钮状态"""
        any_selected = any(
            c.value for c in self._results_column.controls
            if isinstance(c, ft.Checkbox)
        )
        self._download_btn.disabled = not any_selected
        self.update()

    def _do_download(self, e=None) -> None:
        """下载选中的字幕"""
        selected = [
            c.data for c in self._results_column.controls
            if isinstance(c, ft.Checkbox) and c.value
        ]
        if not selected:
            return

        self._download_btn.disabled = True
        self._download_btn.text = "下载中..."
        self.update()

        if self._on_download:
            self._on_download(selected)

    def finish_download(self, success: bool = True, message: str = "") -> None:
        """下载完成后调用"""
        self._download_btn.text = "下载选中"
        self._download_btn.disabled = True
        self._status_text.value = message
        self._status_text.color = AppColors.SUCCESS if success else AppColors.ERROR
        self.update()

    def _close(self, e=None) -> None:
        self.open = False
        self._page.update()

    def show(self) -> None:
        """显示对话框"""
        self.open = True
        self._page.dialog = self
        self._page.update()
