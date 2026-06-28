"""状态指示标签组件

为每个视频状态显示带颜色的标签和图标。
支持状态：缺失、已存在、下载中、已下载、失败。
"""

from __future__ import annotations

import flet as ft

from app.ui.theme import AppColors


# 状态配置映射
STATUS_CONFIG: dict[str, dict] = {
    "missing": {
        "label": "缺失",
        "icon": ft.Icons.ERROR_OUTLINE,
        "color": AppColors.WARNING,
        "color_dark": AppColors.WARNING_DARK,
    },
    "exists": {
        "label": "已存在",
        "icon": ft.Icons.CHECK_CIRCLE,
        "color": AppColors.SUCCESS,
        "color_dark": AppColors.SUCCESS_DARK,
    },
    "downloading": {
        "label": "下载中",
        "icon": ft.Icons.HOURGLASS_BOTTOM,
        "color": AppColors.INFO,
        "color_dark": AppColors.INFO_DARK,
    },
    "downloaded": {
        "label": "已下载",
        "icon": ft.Icons.CHECK_CIRCLE,
        "color": AppColors.SUCCESS,
        "color_dark": AppColors.SUCCESS_DARK,
    },
    "failed": {
        "label": "失败",
        "icon": ft.Icons.CANCEL,
        "color": AppColors.ERROR,
        "color_dark": AppColors.ERROR_DARK,
    },
    "pending": {
        "label": "等待中",
        "icon": ft.Icons.SCHEDULE,
        "color": ft.Colors.GREY_600,
        "color_dark": ft.Colors.GREY_400,
    },
    "searching": {
        "label": "搜索中",
        "icon": ft.Icons.SEARCH,
        "color": AppColors.INFO,
        "color_dark": AppColors.INFO_DARK,
    },
    "unknown": {
        "label": "未知",
        "icon": ft.Icons.HELP_OUTLINE,
        "color": ft.Colors.GREY_500,
        "color_dark": ft.Colors.GREY_500,
    },
}


class StatusBadge(ft.Row):
    """状态指示标签组件

    根据视频的字幕状态显示对应的图标和颜色标签。

    Usage:
        badge = StatusBadge(status="missing")
    """

    def __init__(self, status: str = "unknown", size: str = "normal"):
        """
        Args:
            status: 状态值 (missing/exists/downloading/downloaded/failed/pending/unknown)
            size: 尺寸 ("small" | "normal")
        """
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["unknown"])
        label = config["label"]
        icon = config["icon"]
        color = config["color"]
        text_size = 11 if size == "small" else 13
        icon_size = 14 if size == "small" else 18

        self._icon = ft.Icon(
            icon,
            size=icon_size,
            color=color,
        )
        self._text = ft.Text(
            label,
            size=text_size,
            color=color,
        )

        super().__init__(
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self._icon, self._text],
        )

    def update_status(self, status: str) -> None:
        """更新状态显示"""
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["unknown"])
        self._icon.name = config["icon"]
        self._icon.color = config["color"]
        self._text.value = config["label"]
        self._text.color = config["color"]
        self.update()
