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
from app.downloader.registry import create_provider, list_providers
from app.models.task import DownloadTask, TaskStatus, BatchProgress
from app.models.video import VideoFile
from app.utils.logging import get_logger


# 进度回调类型
ProgressCallback = Callable[[DownloadTask, int, int], None]  # task, current, total


class DownloadCancelled(Exception):
    """下载被取消"""
    pass


logger = get_logger("downloader")


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
        provider_names: Optional[list[str]] = None,
        api_key: str = "",
        proxy: Optional[dict] = None,
    ):
        self.config = config or DownloadConfig()
        if providers is not None:
            self.providers = providers
        elif provider_names:
            self.providers = []
            for name in provider_names:
                p = create_provider(name, api_key=api_key, proxy=proxy)
                if p is not None:
                    self.providers.append(p)
            if not self.providers:
                # 回退：尝试所有已知 provider
                for name in list_providers():
                    p = create_provider(name, api_key=api_key, proxy=proxy)
                    if p is not None:
                        self.providers.append(p)
        else:
            # 默认使用 opensubtitles
            p = create_provider("opensubtitles", api_key=api_key, proxy=proxy)
            self.providers = [p] if p else []
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

        logger.info(f"开始批量下载: {total} 个任务")

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
        """处理单个下载任务：搜索 → 选择 → 下载"""
        video_name = task.video.file_name
        logger.info(f"[下载] 开始处理: {video_name}")
        try:
            # 1. 搜索
            task.start_search()
            provider_names = [p.provider_name for p in self.providers]
            logger.info(f"[下载] 搜索字幕 | 视频={video_name} | provider={provider_names} | 语言={self.config.language_priority}")

            search_result = self._search_subtitles(task.video)
            if self._cancelled:
                logger.info(f"[下载] 已取消: {video_name}")
                task.mark_cancelled()
                return

            if not search_result:
                logger.info(f"[下载] 未找到匹配字幕: {video_name}")
                task.mark_skipped("未找到匹配字幕")
                return

            logger.info(f"[下载] 搜索到 {len(search_result)} 条候选字幕 | 视频={video_name}")
            for i, sr in enumerate(search_result[:5]):
                logger.info(f"[下载]   候选[{i}] id={sr.subtitle_id} 语言={sr.language} 评分={sr.score:.1f}")
            if len(search_result) > 5:
                logger.info(f"[下载]   ... 还有 {len(search_result)-5} 条")

            # 2. 选择最优字幕
            from app.matcher.subtitle_matcher import select_best_subtitles
            selected = select_best_subtitles(
                candidates=search_result,
                language_priority=self.config.language_priority,
                max_count=self.config.max_subtitles_per_video,
            )

            if not selected:
                logger.info(f"[下载] 候选字幕均不符合语言优先级: {video_name} | 优先语言={self.config.language_priority}")
                task.mark_skipped("未找到符合语言优先级的字幕")
                return

            task.subtitles = selected
            task.total_subtitles = len(selected)
            logger.info(f"[下载] 选中 {len(selected)} 个字幕 | 视频={video_name}")
            for i, sub in enumerate(selected):
                logger.info(f"[下载]   选中[{i}] id={sub.subtitle_id} 语言={sub.language} 评分={sub.score:.1f}")

            if self._cancelled:
                logger.info(f"[下载] 已取消: {video_name}")
                task.mark_cancelled()
                return

            # 3. 下载
            task.start_download()
            for idx, sub in enumerate(selected):
                if self._cancelled:
                    task.mark_cancelled()
                    return

                logger.info(f"[下载] 开始下载第 {idx+1}/{len(selected)} 个字幕 | id={sub.subtitle_id} 语言={sub.language}")
                success = self._download_subtitle(task, sub, idx)
                if not success:
                    logger.warning(f"[下载] 第 {idx+1} 个字幕下载失败 | id={sub.subtitle_id}")
                    if task.can_retry():
                        logger.info(f"[下载] 准备重试第 {idx+1} 个字幕...")
                        time.sleep(1)
                        success = self._download_subtitle(task, sub, idx)
                        if success:
                            logger.info(f"[下载] 重试成功 | id={sub.subtitle_id}")
                        else:
                            logger.warning(f"[下载] 重试仍失败 | id={sub.subtitle_id}")
                else:
                    logger.info(f"[下载] 第 {idx+1} 个字幕下载成功 | id={sub.subtitle_id}")

                task.current_subtitle_index = idx + 1
                progress = int((idx + 1) / len(selected) * 100)
                task.update_progress(progress)

            if task.status_enum == TaskStatus.DOWNLOADING:
                task.mark_completed()
                logger.info(f"[下载] 全部完成: {video_name} | 共 {len(selected)} 个字幕")

        except DownloadCancelled:
            logger.info(f"[下载] 已取消: {video_name}")
            task.mark_cancelled()
        except Exception as e:
            logger.error(f"[下载] 处理失败: {video_name} | 错误={e}", exc_info=True)
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
                logger.info(f"[搜索] provider={provider.provider_name} 视频={video.file_name}")
                result = provider.search(params)
                if result.error:
                    logger.warning(f"[搜索] {provider.provider_name} 返回错误: {result.error}")
                elif result.is_success:
                    logger.info(f"[搜索] {provider.provider_name} 找到 {len(result.items)} 条 | 视频={video.file_name}")
                    all_results.extend(result.items)
                else:
                    logger.info(f"[搜索] {provider.provider_name} 未找到结果 | 视频={video.file_name}")
            except Exception as e:
                logger.warning(f"[搜索] {provider.provider_name} 搜索异常: {e} | 视频={video.file_name}")
                continue

        logger.info(f"[搜索] 合计 {len(all_results)} 条候选字幕 | 视频={video.file_name}")
        return all_results

    def _download_subtitle(
        self,
        task: DownloadTask,
        subtitle,
        index: int,
    ) -> bool:
        """下载单个字幕文件到视频目录"""
        video_dir = task.video.path.parent
        video_name = task.video.file_name

        try:
            for provider in self.providers:
                target_provider = getattr(subtitle, 'provider', None) or provider.provider_name
                if provider.provider_name != target_provider and target_provider is not None:
                    continue

                logger.info(f"[下载] 请求 provider={provider.provider_name} 下载 id={subtitle.subtitle_id}")
                try:
                    content, original_name = provider.download(subtitle.subtitle_id)
                except Exception as e:
                    logger.warning(f"[下载] {provider.provider_name} 下载失败: {e}")
                    continue

                if not content:
                    logger.warning(f"[下载] {provider.provider_name} 返回空内容")
                    continue

                logger.info(f"[下载] 收到 {len(content)} 字节 | provider={provider.provider_name} 原始文件名={original_name}")

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
                    logger.info(f"[下载] 跳过已存在的字幕: {target_name} | 路径={target_path}")
                    return True

                # 写入文件
                with open(target_path, "wb") as f:
                    f.write(content)

                logger.info(f"[下载] 已保存: {target_name} | 路径={target_path} | 大小={len(content)}字节")
                return True

        except Exception as e:
            logger.error(f"[下载] 写入文件失败: {video_name} | 错误={e}")
            return False

        logger.warning(f"[下载] 没有可用的 provider 处理 id={subtitle.subtitle_id}")
        return False
