"""下载管理器（调度、队列、并发控制）

管理多个视频的字幕下载任务，支持队列调度、
并发控制、进度追踪和取消操作。
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.downloader.base import BaseProvider, SearchParams
from app.downloader.opensubtitles import OpenSubtitlesProvider
from app.models.task import DownloadTask, TaskStatus, BatchProgress
from app.models.video import VideoFile


# 进度回调类型
ProgressCallback = Callable[[DownloadTask, int, int], None]  # task, current, total


class DownloadCancelled(Exception):
    """下载被取消"""
    pass


@dataclass
class DownloadConfig:
    """下载配置"""
    max_concurrent: int = 3               # 最大并发数
    max_subtitles_per_video: int = 3      # 每视频最大字幕数
    language_priority: list[str] = field(default_factory=lambda: ["zh", "en"])
    timeout: int = 30                     # 请求超时（秒）
    retry_count: int = 2                  # 失败重试次数


class DownloadManager:
    """下载管理器

    管理多个 DownloadTask 的调度和执行。
    支持并发下载、进度追踪、取消操作。
    """

    def __init__(
        self,
        config: Optional[DownloadConfig] = None,
        providers: Optional[list[BaseProvider]] = None,
    ):
        self.config = config or DownloadConfig()
        self.providers = providers or [
            OpenSubtitlesProvider(),
        ]
        self._tasks: list[DownloadTask] = []
        self._cancelled: bool = False
        self._lock = threading.Lock()

    # ── 任务管理 ──────────────────────────────────────────

    @property
    def tasks(self) -> list[DownloadTask]:
        return list(self._tasks)

    @property
    def active_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status_enum.is_active()]

    @property
    def pending_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status == "pending"]

    @property
    def completed_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status == "completed"]

    @property
    def failed_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.status == "failed"]

    @property
    def batch_progress(self) -> BatchProgress:
        return BatchProgress.from_tasks(self._tasks)

    def add_task(self, video: VideoFile) -> DownloadTask:
        """添加单个下载任务"""
        task = DownloadTask(video=video)
        with self._lock:
            self._tasks.append(task)
        return task

    def add_tasks(self, videos: list[VideoFile]) -> list[DownloadTask]:
        """批量添加下载任务"""
        tasks = [DownloadTask(video=v) for v in videos]
        with self._lock:
            self._tasks.extend(tasks)
        return tasks

    def clear_tasks(self) -> None:
        """清除所有任务"""
        with self._lock:
            self._tasks.clear()

    def cancel_all(self) -> None:
        """取消所有任务"""
        self._cancelled = True
        with self._lock:
            for task in self._tasks:
                if not task.is_done:
                    task.mark_cancelled()

    def reset_cancelled(self) -> None:
        """重置取消标志"""
        self._cancelled = False

    # ── 执行 ──────────────────────────────────────────────

    def run_all(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BatchProgress:
        """顺序执行所有待处理任务（含并发控制）

        Args:
            progress_callback: 进度回调

        Returns:
            批量进度汇总
        """
        self.reset_cancelled()
        pending = [t for t in self._tasks if t.status == "pending"]
        total = len(pending)

        if total == 0:
            return self.batch_progress

        completed = 0
        for task in pending:
            if self._cancelled:
                break

            try:
                self._process_task(task)
            except Exception as e:
                task.mark_failed(str(e))

            completed += 1
            if progress_callback:
                progress_callback(task, completed, total)

        return self.batch_progress

    def _process_task(self, task: DownloadTask) -> None:
        """处理单个下载任务：搜索 → 选择 → 下载

        Args:
            task: 下载任务
        """
        try:
            # 1. 搜索
            task.start_search()
            task._log(f"开始搜索: {task.video.file_name}")

            search_result = self._search_subtitles(task.video)
            if self._cancelled:
                task.mark_cancelled()
                return

            if not search_result or len(search_result) == 0:
                task.mark_skipped("未找到匹配字幕")
                return

            # 2. 选择最优字幕
            from app.matcher.subtitle_matcher import select_best_subtitles
            selected = select_best_subtitles(
                candidates=search_result,
                language_priority=self.config.language_priority,
                max_count=self.config.max_subtitles_per_video,
            )

            if not selected:
                task.mark_skipped("未找到符合语言优先级的字幕")
                return

            task.subtitles = selected
            task.total_subtitles = len(selected)
            task._log(f"找到 {len(selected)} 个字幕")

            if self._cancelled:
                task.mark_cancelled()
                return

            # 3. 下载
            task.start_download()
            for idx, sub in enumerate(selected):
                if self._cancelled:
                    task.mark_cancelled()
                    return

                success = self._download_subtitle(task, sub, idx)
                if not success and task.status_enum == TaskStatus.FAILED:
                    if task.can_retry():
                        task._log(f"准备重试...")
                        time.sleep(1)
                        success = self._download_subtitle(task, sub, idx)

                task.current_subtitle_index = idx + 1
                progress = int((idx + 1) / len(selected) * 100)
                task.update_progress(progress)

            if task.status_enum == TaskStatus.DOWNLOADING:
                task.mark_completed()
                task._log("下载完成")

        except DownloadCancelled:
            task.mark_cancelled()
        except Exception as e:
            task.mark_failed(str(e))

    def _search_subtitles(self, video: VideoFile) -> list:
        """跨多源搜索字幕，合并结果"""
        all_results = []

        for provider in self.providers:
            if self._cancelled:
                raise DownloadCancelled()

            try:
                params = SearchParams(
                    file_name=video.file_name,
                    languages=self.config.language_priority,
                    max_count=self.config.max_subtitles_per_video * 3,
                )
                result = provider.search(params)
                if result.is_success:
                    all_results.extend(result.items)
            except Exception as e:
                continue  # 一个源失败不影响其他源

        return all_results

    def _download_subtitle(
        self,
        task: DownloadTask,
        subtitle,
        index: int,
    ) -> bool:
        """下载单个字幕文件到视频目录

        Args:
            task: 父任务
            subtitle: 字幕信息对象
            index: 当前索引

        Returns:
            是否成功
        """
        video_dir = task.video.path.parent

        try:
            for provider in self.providers:
                target_provider = getattr(subtitle, 'provider', None) or provider.provider_name
                if provider.provider_name != target_provider and target_provider is not None:
                    # 先跳过，用匹配的 provider
                    pass

                try:
                    content, original_name = provider.download(subtitle.subtitle_id)
                except Exception:
                    continue

                # 生成目标文件名
                video_stem = task.video.file_name_without_ext
                ext = os.path.splitext(original_name)[1] or ".srt"
                if index == 0:
                    target_name = f"{video_stem}{ext}"
                else:
                    lang_suffix = subtitle.language or f"sub{index + 1}"
                    target_name = f"{video_stem}.{lang_suffix}{ext}"

                target_path = video_dir / target_name

                # 检查是否已存在
                if target_path.exists():
                    task._log(f"跳过已存在的字幕: {target_name}")
                    return True

                # 写入文件
                with open(target_path, "wb") as f:
                    f.write(content)

                task._log(f"已下载: {target_name}")
                return True

        except Exception as e:
            task._log(f"下载失败: {e}")
            return False

        return False
