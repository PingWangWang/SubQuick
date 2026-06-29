"""进度条面板组件

同时支持扫描进度和下载进度两种模式。
实时显示进度百分比、当前文件名、统计汇总。
"""

from __future__ import annotations

import flet as ft
from typing import Optional, Callable

from app.ui.theme import AppColors


class ProgressPanel(ft.Container):
    """进度条面板组件

    可用于扫描阶段或下载阶段，通过 set_mode 切换。

    Usage:
        panel = ProgressPanel()
        panel.start_scanning()          # 进入扫描模式
        panel.update_scan("file.mp4", 50, 100)
        panel.finish("扫描完成")
    """

    def __init__(self):
        self._mode: str = "idle"  # idle | scanning | downloading
        self._progress_bar = ft.ProgressBar(
            bar_height=8,
            value=0,
            color=AppColors.PRIMARY,
            bgcolor="#E0E0E0",
        )
        self._progress_text = ft.Text(
            "就绪",
            size=13,
            color=ft.Colors.GREY_600,
        )
        self._current_file = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_500,
            italic=True,
        )
        self._stats_row = ft.Row(
            spacing=16,
            visible=False,
            controls=[],
        )

        content_column = ft.Column(
            spacing=4,
            controls=[
                ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._progress_bar,
                        self._progress_text,
                    ],
                ),
                self._current_file,
                self._stats_row,
            ],
        )

        super().__init__(
            content=content_column,
            padding=ft.Padding(left=16, right=16, top=8, bottom=8),
            bgcolor=ft.Colors.with_opacity(0.05, AppColors.PRIMARY),
        )

    def _set_bar_width(self, width: int) -> None:
        """由外部调用，设置进度条宽度与容器匹配"""
        self._progress_bar.width = width

    # ── 模式切换 ──────────────────────────────────────────

    def set_scan_mode(self) -> None:
        """切换为扫描模式"""
        self._mode = "scanning"
        self._progress_bar.color = AppColors.INFO
        self.visible = True
        self._stats_row.visible = False

    def set_download_mode(self) -> None:
        """切换为下载模式"""
        self._mode = "downloading"
        self._progress_bar.color = AppColors.PRIMARY
        self.visible = True
        self._stats_row.visible = False

    def set_idle(self) -> None:
        """切换到空闲状态"""
        self._mode = "idle"
        self.visible = False
        self._progress_bar.value = 0
        self._progress_text.value = "就绪"
        self._current_file.value = ""

    # ── 进度更新 ──────────────────────────────────────────

    def update_scan(
        self, current_file: str, processed: int, total: int
    ) -> None:
        """更新扫描进度

        Args:
            current_file: 当前扫描的文件路径
            processed: 已处理文件数
            total: 总文件数（估计）
        """
        self._mode = "scanning"
        self.visible = True

        if total > 0:
            value = min(processed / total, 1.0)
            percent = int(value * 100)
            self._progress_bar.value = value
            self._progress_text.value = f"{percent}% ({processed}/{total})"
        else:
            self._progress_bar.value = None  # 不确定模式
            self._progress_text.value = f"已扫描 {processed} 个文件"

        # 显示当前文件名（取最后部分）
        if current_file:
            import os
            name = os.path.basename(current_file)
            if len(name) > 60:
                name = "..." + name[-57:]
            self._current_file.value = f"当前: {name}"
        else:
            self._current_file.value = ""

    def update_download(
        self,
        current_video: str,
        completed: int,
        total: int,
        status_text: str = "",
    ) -> None:
        """更新下载进度

        Args:
            current_video: 当前下载的视频名
            completed: 已完成数
            total: 总任务数
            status_text: 状态描述，如"正在搜索..."
        """
        self._mode = "downloading"
        self.visible = True

        if total > 0:
            value = min(completed / total, 1.0)
            percent = int(value * 100)
            self._progress_bar.value = value
            self._progress_text.value = f"{percent}% ({completed}/{total})"
        else:
            self._progress_bar.value = None
            self._progress_text.value = f"已完成 {completed} 个"

        if current_video:
            name = current_video
            if len(name) > 60:
                name = "..." + name[-57:]
            status = status_text or "处理中"
            self._current_file.value = f"{status}: {name}"
        else:
            self._current_file.value = ""

    def show_stats(self, stats: dict[str, int]) -> None:
        """显示统计汇总（完成/失败/跳过）

        Args:
            stats: 统计字典，如 {"completed": 5, "failed": 1}
        """
        colors = {
            "completed": AppColors.SUCCESS,
            "failed": AppColors.ERROR,
            "skipped": AppColors.WARNING,
            "cancelled": ft.Colors.GREY_600,
        }
        labels = {
            "completed": "完成",
            "failed": "失败",
            "skipped": "跳过",
            "cancelled": "取消",
        }

        controls = []
        for key in ("completed", "failed", "skipped", "cancelled"):
            count = stats.get(key, 0)
            if count > 0:
                controls.append(
                    ft.Text(
                        f"{labels[key]}: {count}",
                        size=12,
                        color=colors.get(key, ft.Colors.GREY_600),
                    )
                )

        if controls:
            self._stats_row.controls = controls
            self._stats_row.visible = True

    def finish(self, message: str, success: bool = True) -> None:
        """完成进度

        Args:
            message: 完成消息
            success: 是否成功
        """
        self._progress_bar.value = 1.0
        self._progress_bar.color = AppColors.SUCCESS if success else AppColors.ERROR
        self._progress_text.value = message
        self._current_file.value = ""
