"""视频列表 DataTable 组件

可排序、可筛选的视频列表表格。
显示序号、勾选、文件名、格式、大小、时长、字幕状态、目录等列。
"""

from __future__ import annotations

import flet as ft
from typing import Callable, Optional

from app.models.video import VideoFile
from app.ui.components.status_badge import StatusBadge
from app.ui.theme import AppColors


# 列定义
COLUMN_DEFS = [
    {"key": "select", "label": "", "width": 40, "sortable": False},
    {"key": "file_name", "label": "文件名", "width": 260, "sortable": True},
    {"key": "extension", "label": "格式", "width": 60, "sortable": True},
    {"key": "formatted_size", "label": "大小", "width": 80, "sortable": True},
    {"key": "duration_str", "label": "时长", "width": 70, "sortable": True},
    {"key": "subtitle_status", "label": "字幕状态", "width": 100, "sortable": True},
    {"key": "directory", "label": "目录", "width": 200, "sortable": True},
]


class VideoTable(ft.Container):
    """视频列表表格组件

    支持：
    - 全选/反选
    - 点击列头排序
    - 按格式筛选
    - 双击行打开手动搜索
    - 选中计数
    """

    def __init__(
        self,
        on_selection_change: Optional[Callable] = None,
        on_double_click: Optional[Callable] = None,
        page: Optional[ft.Page] = None,
    ):
        self._on_selection_change = on_selection_change
        self._on_double_click = on_double_click
        self._page = page
        self._videos: list[VideoFile] = []
        self._filtered_videos: list[VideoFile] = []
        self._selected_indices: set[int] = set()
        self._sort_column: str = ""
        self._sort_ascending: bool = True
        self._filter_format: str = "全部"

        # 表头控件
        self._select_all_cb = ft.Checkbox(
            tristate=False,
            on_change=self._on_select_all,
        )
        self._count_text = ft.Text(
            "共 0 部视频",
            size=13,
            color=ft.Colors.GREY_600,
        )

        # 排序指示器
        self._sort_indicators: dict[str, ft.Icon] = {}

        # DataTable
        self._table = ft.DataTable(
            column_spacing=12,
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_200),
            heading_row_color=ft.Colors.with_opacity(0.05, AppColors.PRIMARY),
            columns=self._build_columns(),
            rows=[],
            show_checkbox_column=False,
        )

        # 工具栏
        toolbar = ft.Container(
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._select_all_cb,
                    ft.Text("全选", size=13),
                    ft.VerticalDivider(width=1),
                    ft.TextButton("反选", on_click=self._invert_selection),
                    ft.VerticalDivider(width=1),
                    ft.Dropdown(
                        label="筛选",
                        width=120,
                        options=[ft.dropdown.Option("全部")],
                        value="全部",
                        on_change=self._on_filter_change,
                    ),
                    ft.Container(expand=True),
                    self._count_text,
                ],
            ),
            padding=ft.Padding(bottom=4),
        )

        # 主体内容
        content_column = ft.Column(
            spacing=4,
            controls=[
                toolbar,
                ft.Column(
                    controls=[self._table],
                    scroll=ft.ScrollMode.AUTO,
                    height=400,
                ),
            ],
        )

        super().__init__(
            content=content_column,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=8,
            padding=8,
        )

    # ── 列构建 ────────────────────────────────────────────

    def _build_columns(self) -> list[ft.DataColumn]:
        """构建表头列"""
        columns = []
        for col_def in COLUMN_DEFS:
            if col_def["sortable"]:
                # 可排序列带排序图标
                icon = ft.Icon(
                    name=ft.Icons.ARROW_UPWARD,
                    size=14,
                    visible=False,
                    color=AppColors.PRIMARY,
                )
                self._sort_indicators[col_def["key"]] = icon

                label = ft.Row(
                    spacing=4,
                    controls=[
                        ft.Text(col_def["label"], size=13, weight=ft.FontWeight.W_600),
                        icon,
                    ],
                    on_click=lambda e, k=col_def["key"]: self._on_sort(k),
                )
                columns.append(
                    ft.DataColumn(
                        label=label,
                        on_sort=lambda e, k=col_def["key"]: self._on_sort(k),
                    )
                )
            else:
                columns.append(ft.DataColumn(ft.Text("")))
        return columns

    # ── 数据设置 ──────────────────────────────────────────

    def set_videos(self, videos: list[VideoFile]) -> None:
        """设置视频数据

        Args:
            videos: 视频文件列表
        """
        self._videos = videos
        self._selected_indices.clear()
        self._build_filter_options(videos)
        self._apply_filter()

    def _build_filter_options(self, videos: list[VideoFile]) -> None:
        """从视频数据构建筛选选项"""
        formats = sorted(set(v.extension.lstrip(".").upper() for v in videos))
        formats = ["全部"] + formats + ["缺失字幕", "已有字幕"]
        dropdown = self._find_dropdown()
        if dropdown:
            dropdown.options = [ft.dropdown.Option(f) for f in formats]
            dropdown.value = "全部"

    def _find_dropdown(self) -> Optional[ft.Dropdown]:
        """查找筛选下拉框控件"""
        # 遍历查找
        for c in self.content.controls[0].content.controls if hasattr(self, 'content') else []:
            if isinstance(c, ft.Dropdown):
                return c
            if isinstance(c, ft.Row):
                for r in c.controls:
                    if isinstance(r, ft.Dropdown):
                        return r
        return None

    # ── 筛选 ──────────────────────────────────────────────

    def _on_filter_change(self, e) -> None:
        """筛选条件变更"""
        self._filter_format = e.control.value
        self._apply_filter()

    def _apply_filter(self) -> None:
        """应用筛选和排序"""
        # 筛选
        videos = self._videos
        fmt = self._filter_format
        if fmt and fmt != "全部":
            if fmt == "缺失字幕":
                videos = [v for v in videos if v.subtitle_status == "missing"]
            elif fmt == "已有字幕":
                videos = [v for v in videos if v.subtitle_status == "exists"]
            else:
                videos = [v for v in videos if v.extension.lstrip(".").upper() == fmt]

        self._filtered_videos = videos

        # 排序
        if self._sort_column:
            reverse = not self._sort_ascending
            self._filtered_videos.sort(
                key=lambda v: self._get_sort_key(v, self._sort_column),
                reverse=reverse,
            )

        # 更新数据行
        self._rebuild_rows()
        self._update_count()

    def _get_sort_key(self, video: VideoFile, column: str):
        """获取排序键值"""
        if column == "file_name":
            return video.file_name.lower()
        elif column == "extension":
            return video.extension
        elif column == "formatted_size":
            return video.file_size
        elif column == "duration_str":
            return video.duration
        elif column == "subtitle_status":
            return video.subtitle_status
        elif column == "directory":
            return video.directory.lower()
        return ""

    def _on_sort(self, column: str) -> None:
        """排序列点击"""
        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True

        # 更新排序指示器
        for key, icon in self._sort_indicators.items():
            if key == column:
                icon.visible = True
                icon.name = ft.Icons.ARROW_UPWARD if self._sort_ascending else ft.Icons.ARROW_DOWNWARD
            else:
                icon.visible = False

        self._apply_filter()

    # ── 行构建 ────────────────────────────────────────────

    def _rebuild_rows(self) -> None:
        """重新构建所有数据行"""
        rows = []
        for idx, video in enumerate(self._filtered_videos):
            is_selected = idx in self._selected_indices
            row = self._build_row(video, idx, is_selected)
            rows.append(row)
        self._table.rows = rows
        self.update()

    def _build_row(self, video: VideoFile, idx: int, selected: bool) -> ft.DataRow:
        """构建单行数据"""
        # 颜色指示
        row_color = None
        if video.subtitle_status == "missing":
            row_color = ft.Colors.with_opacity(0.03, AppColors.WARNING)
        elif video.subtitle_status == "exists":
            row_color = ft.Colors.with_opacity(0.03, AppColors.SUCCESS)

        cb = ft.Checkbox(
            value=selected,
            on_change=lambda e, i=idx: self._on_row_select(i, e.control.value),
        )
        status_badge = StatusBadge(status=video.subtitle_status, size="small")

        # 截断长文件名
        display_name = video.file_name
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        # 截断长目录
        display_dir = video.directory
        if len(display_dir) > 30:
            parts = display_dir.replace("\\", "/").split("/")
            if len(parts) > 3:
                display_dir = ".../" + "/".join(parts[-2:])

        cells = [
            ft.DataCell(cb),
            ft.DataCell(
                ft.Text(display_name, size=12),
                on_double_tap=lambda e, v=video: self._on_double_click(v) if self._on_double_click else None,
            ),
            ft.DataCell(ft.Text(video.extension.lstrip(".").upper(), size=12)),
            ft.DataCell(ft.Text(video.formatted_size, size=12)),
            ft.DataCell(ft.Text(video.duration_str, size=12)),
            ft.DataCell(status_badge),
            ft.DataCell(ft.Text(display_dir, size=11, color=ft.Colors.GREY_500, italic=True)),
        ]

        return ft.DataRow(
            cells=cells,
            color=row_color,
            on_long_press=lambda e, v=video: self._on_double_click(v) if self._on_double_click else None,
        )

    # ── 选择管理 ──────────────────────────────────────────

    def _on_row_select(self, idx: int, selected: bool) -> None:
        """单行选择/取消"""
        if selected:
            self._selected_indices.add(idx)
        else:
            self._selected_indices.discard(idx)

        # 更新全选状态
        self._sync_select_all()
        self._update_count()
        self._on_selection_change and self._on_selection_change()

    def _on_select_all(self, e) -> None:
        """全选/取消全选"""
        if e.control.value:
            self._selected_indices = set(range(len(self._filtered_videos)))
        else:
            self._selected_indices.clear()
        self._rebuild_rows()
        self._update_count()
        self._on_selection_change and self._on_selection_change()

    def _invert_selection(self, e=None) -> None:
        """反选"""
        all_indices = set(range(len(self._filtered_videos)))
        self._selected_indices = all_indices - self._selected_indices
        self._rebuild_rows()
        self._update_count()
        self._sync_select_all()
        self._on_selection_change and self._on_selection_change()

    def _sync_select_all(self) -> None:
        """同步全选复选框状态"""
        total = len(self._filtered_videos)
        selected = len(self._selected_indices)
        if total == 0:
            self._select_all_cb.value = False
        elif selected == total:
            self._select_all_cb.value = True
        else:
            self._select_all_cb.value = None  # 部分选中

    def _update_count(self) -> None:
        """更新统计文字"""
        total = len(self._filtered_videos)
        selected = len(self._selected_indices)
        parts = [f"共 {total} 部"]
        if self._filter_format != "全部":
            parts.insert(0, f"[{self._filter_format}]")
        if selected > 0:
            parts.append(f"已选 {selected} 部")
        self._count_text.value = " | ".join(parts)

    # ── 双击回调 ──────────────────────────────────────────

    def _on_double_click(self, video: VideoFile) -> None:
        """双击行触发手动搜索"""
        if self._on_double_click:
            self._on_double_click(video)

    # ── 对外接口 ──────────────────────────────────────────

    def get_selected_videos(self) -> list[VideoFile]:
        """获取所有选中的视频"""
        return [self._filtered_videos[i] for i in sorted(self._selected_indices)]

    def clear_selection(self) -> None:
        """清除所有选择"""
        self._selected_indices.clear()
        self._sync_select_all()
        self._rebuild_rows()
        self._update_count()
