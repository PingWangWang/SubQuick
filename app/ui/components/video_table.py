"""视频列表组件（基于 ft.Row 自定义布局，确保宽度填满）

支持全选/反选、排序、筛选、双击搜索。
"""

from __future__ import annotations

import flet as ft
from typing import Callable, Optional

from app.models.video import VideoFile
from app.ui.components.status_badge import StatusBadge
from app.ui.theme import AppColors


# 列定义
# flex: 空间分配权重（0 = 不伸缩，按内容宽度）
COLUMN_DEFS = [
    {"key": "select",    "label": "",       "flex": 0, "sortable": False},
    {"key": "file_name", "label": "文件名",  "flex": 4, "sortable": True},
    {"key": "extension", "label": "格式",    "flex": 1, "sortable": True},
    {"key": "formatted_size", "label": "大小", "flex": 1, "sortable": True},
    {"key": "duration_str", "label": "时长",  "flex": 1, "sortable": True},
    {"key": "subtitle_status", "label": "字幕状态", "flex": 2, "sortable": True},
    {"key": "directory", "label": "目录",    "flex": 3, "sortable": True},
]


def _build_data_cell(content: ft.Control, flex: int = 1, **kwargs) -> ft.Container:
    """构建数据单元格"""
    return ft.Container(
        content=content,
        expand=flex,
        padding=ft.Padding(left=4, right=4, top=0, bottom=0),
        **kwargs,
    )


class VideoTable(ft.Container):
    """视频列表表格组件"""

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
        self._row_containers: list[ft.Container] = []  # 用于刷新行

        # 全选复选框
        self._select_all_cb = ft.Checkbox(tristate=False, on_change=self._on_select_all)
        self._count_text = ft.Text("共 0 部视频", size=13, color=ft.Colors.GREY_600)

        # 排序指示器
        self._sort_indicators: dict[str, ft.Icon] = {}

        # 表头行
        header_cells = []
        for col_def in COLUMN_DEFS:
            if col_def["sortable"]:
                icon = ft.Icon(ft.Icons.ARROW_UPWARD, size=14, visible=False, color=AppColors.PRIMARY)
                self._sort_indicators[col_def["key"]] = icon
                label = ft.Row(
                    spacing=4,
                    controls=[ft.Text(col_def["label"], size=13, weight=ft.FontWeight.W_600), icon],
                )
                cell = ft.Container(
                    content=label,
                    expand=col_def["flex"] if col_def["flex"] else None,
                    padding=ft.Padding(left=4, right=4, top=0, bottom=0),
                    on_click=lambda _, k=col_def["key"]: self._on_sort(k),
                )
            else:
                cell = ft.Container(content=ft.Text(""), width=40)  # checkbox 列固定宽度
            header_cells.append(cell)

        header_row = ft.Container(
            content=ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(content=self._select_all_cb, width=40),
                    *header_cells[1:],
                ],
            ),
            bgcolor=ft.Colors.with_opacity(0.05, AppColors.PRIMARY),
            padding=ft.Padding(left=0, right=0, top=8, bottom=8),
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
        )

        # 筛选下拉框
        self._filter_dropdown = ft.Dropdown(
            label="筛选",
            width=120,
            options=[ft.dropdown.Option("全部")],
            value="全部",
            on_select=self._on_filter_change,
        )

        # 工具栏
        toolbar = ft.Container(
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("全选", size=13),
                    ft.VerticalDivider(width=1),
                    ft.TextButton("反选", on_click=self._invert_selection),
                    ft.VerticalDivider(width=1),
                    self._filter_dropdown,
                    ft.Container(expand=True),
                    self._count_text,
                ],
            ),
            padding=ft.Padding(left=0, right=0, top=0, bottom=4),
        )

        # 数据行容器（可滚动）
        self._rows_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        # 整体布局
        content_column = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                toolbar,
                header_row,
                self._rows_column,
            ],
        )

        super().__init__(
            content=content_column,
            expand=True,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
            padding=8,
        )

    # ── 数据设置 ──────────────────────────────────────────

    def set_videos(self, videos: list[VideoFile]) -> None:
        self._videos = videos
        self._selected_indices.clear()
        self._build_filter_options(videos)
        self._apply_filter()

    def _build_filter_options(self, videos: list[VideoFile]) -> None:
        formats = sorted(set(v.extension.lstrip(".").upper() for v in videos))
        formats = ["全部"] + formats + ["缺失字幕", "已有字幕"]
        self._filter_dropdown.options = [ft.dropdown.Option(f) for f in formats]
        self._filter_dropdown.value = "全部"

    # ── 筛选与排序 ────────────────────────────────────────

    def _on_filter_change(self, e) -> None:
        self._filter_format = e.control.value
        self._apply_filter()

    def _apply_filter(self) -> None:
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

        if self._sort_column:
            reverse = not self._sort_ascending
            self._filtered_videos.sort(
                key=lambda v: self._get_sort_key(v, self._sort_column),
                reverse=reverse,
            )

        self._rebuild_rows()
        self._update_count()

    def _get_sort_key(self, video: VideoFile, column: str):
        m = {
            "file_name": video.file_name.lower(),
            "extension": video.extension,
            "formatted_size": video.file_size,
            "duration_str": video.duration,
            "subtitle_status": video.subtitle_status,
            "directory": video.directory.lower(),
        }
        return m.get(column, "")

    def _on_sort(self, column: str) -> None:
        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True

        for key, icon in self._sort_indicators.items():
            if key == column:
                icon.visible = True
                icon.name = ft.Icons.ARROW_UPWARD if self._sort_ascending else ft.Icons.ARROW_DOWNWARD
            else:
                icon.visible = False

        self._apply_filter()

    # ── 行构建 ────────────────────────────────────────────

    def _rebuild_rows(self) -> None:
        rows = []
        self._row_containers = []
        for idx, video in enumerate(self._filtered_videos):
            is_selected = idx in self._selected_indices
            row = self._build_row(video, idx, is_selected)
            rows.append(row)
            self._row_containers.append(row)
        self._rows_column.controls = rows
        self.update()

    def _build_row(self, video: VideoFile, idx: int, selected: bool) -> ft.Container:
        """构建一行数据"""
        # 行背景色
        bg = None
        if video.subtitle_status == "missing":
            bg = ft.Colors.with_opacity(0.03, AppColors.WARNING)
        elif video.subtitle_status == "exists":
            bg = ft.Colors.with_opacity(0.03, AppColors.SUCCESS)

        cb = ft.Checkbox(value=selected, on_change=lambda e, i=idx: self._on_row_select(i, e.control.value))

        display_name = video.file_name
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        display_dir = video.directory
        if len(display_dir) > 30:
            parts = display_dir.replace("\\", "/").split("/")
            if len(parts) > 3:
                display_dir = ".../" + "/".join(parts[-2:])

        status_badge = StatusBadge(status=video.subtitle_status, size="small")

        row = ft.Container(
            content=ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(content=cb, width=40),
                    _build_data_cell(ft.Text(display_name, size=12), flex=4,
                        on_click=lambda e, v=video: self._on_double_click(v) if self._on_double_click else None),
                    _build_data_cell(ft.Text(video.extension.lstrip(".").upper(), size=12), flex=1),
                    _build_data_cell(ft.Text(video.formatted_size, size=12), flex=1),
                    _build_data_cell(ft.Text(video.duration_str, size=12), flex=1),
                    _build_data_cell(status_badge, flex=2),
                    _build_data_cell(ft.Text(display_dir, size=11, color=ft.Colors.GREY_500, italic=True), flex=3),
                ],
            ),
            bgcolor=bg,
            padding=ft.Padding(left=0, right=0, top=6, bottom=6),
            border=ft.Border(bottom=ft.BorderSide(0.5, ft.Colors.GREY_200)),
        )
        return row

    # ── 选择管理 ──────────────────────────────────────────

    def _on_row_select(self, idx: int, selected: bool) -> None:
        if selected:
            self._selected_indices.add(idx)
        else:
            self._selected_indices.discard(idx)
        self._sync_select_all()
        self._update_count()
        self._on_selection_change and self._on_selection_change()

    def _on_select_all(self, e) -> None:
        if e.control.value:
            self._selected_indices = set(range(len(self._filtered_videos)))
        else:
            self._selected_indices.clear()
        self._rebuild_rows()
        self._update_count()
        self._on_selection_change and self._on_selection_change()

    def _invert_selection(self, e=None) -> None:
        all_indices = set(range(len(self._filtered_videos)))
        self._selected_indices = all_indices - self._selected_indices
        self._rebuild_rows()
        self._update_count()
        self._sync_select_all()
        self._on_selection_change and self._on_selection_change()

    def _sync_select_all(self) -> None:
        total = len(self._filtered_videos)
        selected = len(self._selected_indices)
        if total == 0:
            self._select_all_cb.value = False
        elif selected == total:
            self._select_all_cb.value = True
        else:
            self._select_all_cb.value = None

    def _update_count(self) -> None:
        total = len(self._filtered_videos)
        selected = len(self._selected_indices)
        parts = [f"共 {total} 部"]
        if self._filter_format != "全部":
            parts.insert(0, f"[{self._filter_format}]")
        if selected > 0:
            parts.append(f"已选 {selected} 部")
        self._count_text.value = " | ".join(parts)

    # ── 双击 ──────────────────────────────────────────────

    def _on_double_click(self, video: VideoFile) -> None:
        if self._on_double_click:
            self._on_double_click(video)

    # ── 对外接口 ──────────────────────────────────────────

    def get_selected_videos(self) -> list[VideoFile]:
        return [self._filtered_videos[i] for i in sorted(self._selected_indices)]

    def clear_selection(self) -> None:
        self._selected_indices.clear()
        self._sync_select_all()
        self._rebuild_rows()
        self._update_count()
