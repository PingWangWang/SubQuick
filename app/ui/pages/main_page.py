"""主页面 — 扫描面板 + 视频列表 + 操作/进度面板

完整的 16:9 宽屏布局页面。
"""

from __future__ import annotations

import os
import threading
import flet as ft
from typing import Optional

from app.ui.theme import AppColors
from app.ui.app import SubQuickApp
from app.ui.components.video_table import VideoTable
from app.ui.components.progress_panel import ProgressPanel
from app.ui.components.search_dialog import SearchDialog
from app.models.video import VideoFile
from app.models.task import DownloadTask, BatchProgress
from app.scanner import scan_directory, FileFilter, ScanResult, ScanCancelled
from app.scanner.video_scanner import ProgressCallback
from app.downloader import DownloadManager, DownloadConfig
from app.services.settings_service import SettingsService


class ScanPanel(ft.Container):
    """扫描设置面板：目录选择 + 格式显示 + 开始扫描按钮"""

    def __init__(self, app: SubQuickApp, on_scan_start: callable):
        self._app = app
        self._on_scan_start = on_scan_start

        # 目录输入
        self._dir_field = ft.TextField(
            hint_text="选择视频目录...",
            width=500,
            read_only=True,
            on_click=self._pick_directory,
        )
        self._browse_btn = ft.Button(
            content=ft.Text("浏览目录"),
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._pick_directory,
        )
        self._scan_text = ft.Text("开始扫描")
        self._scan_btn = ft.Button(
            content=self._scan_text,
            icon=ft.Icons.SEARCH,
            on_click=self._on_scan_click,
        )

        # 格式标签
        self._formats_text = ft.Text(
            "支持格式: MP4 MKV AVI MOV WMV",
            size=12,
            color=ft.Colors.GREY_500,
        )

        # 内容行
        row1 = ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.FOLDER, size=20),
                self._dir_field,
                self._browse_btn,
                ft.Container(expand=True),
                self._scan_btn,
            ],
        )

        content = ft.Column(
            spacing=4,
            controls=[row1, self._formats_text],
        )

        super().__init__(
            content=content,
            padding=ft.Padding(left=12, right=12, top=12, bottom=12),
            bgcolor=ft.Colors.with_opacity(0.03, AppColors.PRIMARY),
            border_radius=8,
        )

    def _pick_directory(self, e=None):
        """打开目录选择器"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        directory = filedialog.askdirectory(title="选择视频目录")
        root.destroy()
        if directory:
            self._dir_field.value = directory
            self._dir_field.update()

    def _on_scan_click(self, e=None):
        """点击开始/取消扫描"""
        if self._scan_text.value == "开始扫描":
            directory = self._dir_field.value
            if not directory:
                self._show_snackbar("请先选择视频目录", AppColors.WARNING)
                return
            if not os.path.isdir(directory):
                self._show_snackbar(f"目录不存在: {directory}", AppColors.ERROR)
                return
            self._scan_text.value = "取消扫描"
            self._scan_btn.icon = ft.Icons.CANCEL
            self._dir_field.disabled = True
            self._browse_btn.disabled = True
            self.update()
            if self._on_scan_start:
                self._on_scan_start(directory)
        else:
            if self._on_scan_start:
                self._on_scan_start(None)  # 取消

    def reset_scan_button(self):
        """恢复扫描按钮"""
        self._scan_text.value = "开始扫描"
        self._scan_btn.icon = ft.Icons.SEARCH
        self._dir_field.disabled = False
        self._browse_btn.disabled = False
        self.update()

    def get_directory(self) -> str:
        return self._dir_field.value or ""

    def _show_snackbar(self, message: str, color: str = AppColors.ERROR):
        """显示通知消息"""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=color,
            )
            self.page.snack_bar.open = True
            self.page.update()


class ActionPanel(ft.Container):
    """操作面板：一键匹配 + 导出 + 状态统计"""

    def __init__(self, app: SubQuickApp, on_download: callable, on_export: callable):
        self._on_download = on_download
        self._on_export = on_export
        self._app = app

        self._download_text = ft.Text("一键匹配")
        self._download_btn = ft.Button(
            content=self._download_text,
            icon=ft.Icons.DOWNLOAD,
            disabled=True,
            on_click=lambda e: self._on_download(),
        )
        self._export_btn = ft.OutlinedButton(
            content=ft.Text("导出缺失列表"),
            icon=ft.Icons.FILE_DOWNLOAD,
            disabled=True,
            on_click=lambda e: self._on_export(),
        )

        content = ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self._download_btn,
                self._export_btn,
                ft.Container(expand=True),
            ],
        )

        super().__init__(
            content=content,
            padding=ft.Padding(left=8, right=8, top=8, bottom=8),
        )

    def set_buttons_enabled(self, enabled: bool):
        """设置操作按钮启用状态"""
        self._download_btn.disabled = not enabled
        self._export_btn.disabled = not enabled
        self.update()

    def set_download_mode(self, active: bool):
        """切换下载模式"""
        if active:
            self._download_text.value = "下载中..."
            self._download_btn.icon = ft.Icons.HOURGLASS_BOTTOM
            self._download_btn.disabled = True
        else:
            self._download_text.value = "一键匹配"
            self._download_btn.icon = ft.Icons.DOWNLOAD
        self.update()


class MainPage(ft.Column):
    """主页面 — 16:9 宽屏布局

    从上到下：
    1. Header
    2. 扫描面板
    3. 进度条
    4. 视频列表
    5. 操作面板
    6. 状态栏
    """

    def __init__(self, app: SubQuickApp):
        self._app = app
        self._scan_result: Optional[ScanResult] = None
        self._cancel_scan = False
        self._download_manager: Optional[DownloadManager] = None

        # ── 创建子组件 ──────────────────────────────────

        # Header
        self._header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.MOVIE, size=24, color=AppColors.PRIMARY),
                            ft.Text("SubQuick", size=20, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS,
                        tooltip="设置",
                        on_click=lambda e: app.navigate_to("settings"),
                    ),
                ],
            ),
            padding=ft.Padding(left=16, right=8, top=8, bottom=4),
        )

        # 扫描面板
        self._scan_panel = ScanPanel(app, self._on_scan_start)

        # 进度条面板
        self._progress_panel = ProgressPanel()

        # 视频列表
        self._video_table = VideoTable(
            on_selection_change=self._on_selection_change,
            on_double_click=self._on_video_double_click,
        )

        # 操作面板
        self._action_panel = ActionPanel(
            app,
            on_download=self._start_download,
            on_export=self._export_missing_list,
        )

        # 状态栏
        self._status_bar = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("就绪", size=12, color=ft.Colors.GREY_500),
                    ft.Container(expand=True),
                    ft.Text("", size=12, color=ft.Colors.GREY_500),
                ],
            ),
            padding=ft.Padding(left=16, right=16, top=4, bottom=4),
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.GREY),
        )

        # ── 布局（垂直堆叠 16:9） ──────────────────────

        super().__init__(
            spacing=4,
            expand=True,
            controls=[
                self._header,
                ft.Container(
                    content=ft.Column(
                        spacing=8,
                        expand=True,
                        controls=[
                            self._scan_panel,
                            self._progress_panel,
                            self._video_table,
                            self._action_panel,
                        ],
                    ),
                    padding=ft.Padding(left=16, right=16),
                    expand=True,
                ),
                self._status_bar,
            ],
        )

    # ── 扫描流程 ──────────────────────────────────────────

    def _on_scan_start(self, directory: str) -> None:
        """开始扫描（在后台线程中执行）"""
        if directory is None:
            self._cancel_scan = True
            return

        self._cancel_scan = False
        self._progress_panel.set_scan_mode()
        self._progress_panel.update_scan("准备扫描...", 0, 0)
        self._progress_panel.update()
        self._video_table.set_videos([])
        self._action_panel.set_buttons_enabled(False)
        self._update_status("正在扫描...")
        self.update()

        page = self._app.page

        def progress_callback(path: str, current: int, total: int, phase: str):
            async def _update_ui():
                self._progress_panel.update_scan(path, current, total)
                self._progress_panel.update()
                page.update()
            page.run_task(_update_ui)

        def _run_on_main(func, *args):
            """在后台线程中调用，将 func 调度到主线程执行"""
            async def wrapper():
                func(*args)
                page.update()
            page.run_task(wrapper)

        def scan_thread():
            try:
                filter_obj = FileFilter(
                    video_formats=self._app.settings.video_formats,
                    ignore_patterns=self._app.settings.ignore_list.patterns,
                    ignore_directories=self._app.settings.ignore_list.directories,
                )
                result = scan_directory(
                    directory=directory,
                    file_filter=filter_obj,
                    recursive=True,
                    progress_callback=progress_callback,
                    cancel_flag=lambda: self._cancel_scan,
                )
                self._scan_result = result
                _run_on_main(self._after_scan, result)
            except ScanCancelled:
                _run_on_main(self._after_scan_cancelled)
            except FileNotFoundError as e:
                _run_on_main(self._after_scan_error, str(e))
            except PermissionError as e:
                _run_on_main(self._after_scan_error, str(e))
            except Exception as e:
                _run_on_main(self._after_scan_error, f"扫描出错: {e}")

        threading.Thread(target=scan_thread, daemon=True).start()

    def _after_scan(self, result: ScanResult) -> None:
        """扫描完成，更新 UI"""
        self._scan_panel.reset_scan_button()
        self._progress_panel.finish(
            f"扫描完成: 发现 {result.total_videos} 部视频",
            success=True,
        )

        # 展示视频列表
        self._video_table.set_videos(result.video_files)

        # 更新操作按钮状态
        has_missing = result.missing_subtitle_count > 0
        self._action_panel.set_buttons_enabled(has_missing)

        # 更新状态栏
        self._update_status(result.summary())
        self.update()

    def _after_scan_cancelled(self) -> None:
        """扫描被取消"""
        self._scan_panel.reset_scan_button()
        self._progress_panel.set_idle()
        self._update_status("扫描已取消")
        self.update()

    def _after_scan_error(self, error_msg: str) -> None:
        """扫描出错"""
        self._scan_panel.reset_scan_button()
        self._progress_panel.finish(error_msg, success=False)
        self._update_status(error_msg)
        self.update()

    # ── 下载流程 ──────────────────────────────────────────

    def _on_selection_change(self) -> None:
        """选中视频变化时更新下载按钮"""
        selected = self._video_table.get_selected_videos()
        missing_selected = [v for v in selected if v.subtitle_status == "missing"]
        self._action_panel.set_buttons_enabled(len(missing_selected) > 0)

    def _start_download(self) -> None:
        """一键匹配：下载所有选中的缺失字幕视频"""
        selected = self._video_table.get_selected_videos()
        selected_missing = [v for v in selected if v.subtitle_status == "missing"]

        if not selected_missing:
            self._show_snackbar("请先勾选需要匹配字幕的视频", AppColors.WARNING)
            return

        # 检查 API Key
        if not self._app.settings.api_key:
            self._show_snackbar("请先在设置中配置 OpenSubtitles API Key", AppColors.WARNING)
            return

        # 切换到下载模式
        self._action_panel.set_download_mode(True)
        self._progress_panel.set_download_mode()
        self._progress_panel.update_download("准备中...", 0, len(selected_missing))
        self._update_status(f"开始下载 {len(selected_missing)} 部字幕...")

        # 创建下载任务
        config = DownloadConfig(
            max_subtitles_per_video=self._app.settings.max_subtitles_per_video,
            language_priority=self._app.settings.language_priority.fallback_chain,
        )
        self._download_manager = DownloadManager(config=config)

        tasks = self._download_manager.add_tasks(selected_missing)

        def progress_callback(task, completed, total):
            async def _update_ui():
                self._progress_panel.update_download(
                    task.video.file_name if task else "",
                    completed, total,
                    task.status_enum.display_name() if task else "",
                )
                self._progress_panel.update()
                self.update()
            self._app.page.run_task(_update_ui)

        def download_thread():
            try:
                batch_progress = self._download_manager.run_all(
                    progress_callback=progress_callback,
                )
                # 回到主线程更新 UI
                self._after_download(batch_progress)
            except Exception as e:
                self._after_download_error(str(e))

        threading.Thread(target=download_thread, daemon=True).start()

    def _after_download(self, batch: BatchProgress) -> None:
        """下载完成，更新 UI"""
        self._action_panel.set_download_mode(False)
        self._progress_panel.finish(batch.summary, success=batch.completed > 0)
        self._progress_panel.show_stats({
            "completed": batch.completed,
            "failed": batch.failed,
            "skipped": batch.skipped,
            "cancelled": batch.cancelled,
        })

        # 重新扫描以更新字幕状态
        if self._scan_panel.get_directory():
            self._on_scan_start(self._scan_panel.get_directory())

        self._update_status(f"下载完成: {batch.summary}")
        self.update()

    def _after_download_error(self, error_msg: str) -> None:
        """下载出错"""
        self._action_panel.set_download_mode(False)
        self._progress_panel.finish(error_msg, success=False)
        self._update_status(error_msg)
        self.update()

    # ── 手动搜索 ──────────────────────────────────────────

    def _on_video_double_click(self, video: VideoFile) -> None:
        """双击视频打开手动搜索"""
        dialog = SearchDialog(
            page=self.page if self.page else ft.Page(),
            video_name=video.file_name,
            video_path=video.directory,
            on_search=self._on_manual_search,
            on_download=self._on_manual_download,
        )
        dialog.show()

    def _on_manual_search(self, params) -> None:
        """手动搜索回调"""
        # 简单实现：使用第一个 provider 搜索
        if self._app.settings.subtitle_providers.get("opensubtitles", {}).get("enabled"):
            from app.downloader import OpenSubtitlesProvider
            provider = OpenSubtitlesProvider(
                api_key=self._app.settings.api_key,
            )
            result = provider.search(params)
            # 更新对话框搜索结果
            if self.page and self.page.dialog:
                dialog = self.page.dialog
                if hasattr(dialog, 'show_results'):
                    items_data = []
                    for item in result.items:
                        items_data.append({
                            "subtitle_id": item.subtitle_id,
                            "language": item.language,
                            "language_display": item.language,
                            "file_name": item.file_name,
                            "score": item.score,
                            "download_url": item.download_url,
                        })
                    dialog.show_results(items_data)

    def _on_manual_download(self, selected: list) -> None:
        """手动下载回调"""
        success_count = 0
        for item in selected:
            try:
                from app.downloader import OpenSubtitlesProvider
                provider = OpenSubtitlesProvider(
                    api_key=self._app.settings.api_key,
                )
                content, file_name = provider.download(item.get("subtitle_id", ""))
                # 简单存放到桌面
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                save_path = os.path.join(desktop, file_name)
                with open(save_path, "wb") as f:
                    f.write(content)
                success_count += 1
            except Exception:
                pass

        if self.page and self.page.dialog:
            dialog = self.page.dialog
            if hasattr(dialog, 'finish_download'):
                dialog.finish_download(
                    success=success_count > 0,
                    message=f"已下载 {success_count} 个字幕到桌面",
                )

    # ── 导出缺失列表 ──────────────────────────────────────

    def _export_missing_list(self) -> None:
        """导出缺失字幕的视频列表为 CSV"""
        if not self._scan_result:
            return

        missing = [v for v in self._scan_result.video_files if v.subtitle_status == "missing"]
        if not missing:
            self._show_snackbar("没有缺失字幕的视频可导出", AppColors.WARNING)
            return

        # 生成 CSV
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["文件名", "格式", "大小", "时长", "目录"])
        for v in missing:
            writer.writerow([v.file_name, v.extension, v.formatted_size, v.duration_str, v.directory])

        # 写入桌面
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop, "SubQuick_缺失字幕列表.csv")
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(output.getvalue())

        self._show_snackbar(f"已导出: {file_path}", AppColors.SUCCESS)

    # ── 辅助方法 ──────────────────────────────────────────

    def _update_status(self, message: str) -> None:
        """更新底部状态栏"""
        self._status_bar.content.controls[0].value = message
        self._status_bar.update()

    def _show_snackbar(self, message: str, color: str = AppColors.ERROR) -> None:
        """显示 Snackbar 通知"""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message, size=14),
                bgcolor=color,
            )
            self.page.snack_bar.open = True
            self.page.update()
