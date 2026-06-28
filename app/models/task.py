"""下载任务数据模型

提供 DownloadTask 数据类，包含任务状态机管理、进度跟踪、
时间记录、统计汇总等功能。
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional

from app.models.video import VideoFile
from app.models.subtitle import SubtitleInfo


class TaskStatus(enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

    @classmethod
    def from_string(cls, value: str) -> "TaskStatus":
        for member in cls:
            if member.value == value:
                return member
        return cls.PENDING

    def display_name(self) -> str:
        names = {
            "pending": "等待中",
            "searching": "搜索中",
            "downloading": "下载中",
            "completed": "已完成",
            "failed": "失败",
            "cancelled": "已取消",
            "skipped": "已跳过",
        }
        return names.get(self.value, self.value)

    def is_terminal(self) -> bool:
        """是否为终止状态（不会再变化）"""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                        TaskStatus.CANCELLED, TaskStatus.SKIPPED)

    def is_active(self) -> bool:
        """是否为进行中状态"""
        return self in (TaskStatus.SEARCHING, TaskStatus.DOWNLOADING)

    def can_transition_to(self, target: "TaskStatus") -> bool:
        """检查状态转换是否合法"""
        # 终止状态除了 FAILED 可以转到 PENDING 重试外，其他不能转换
        if self.is_terminal() and self != TaskStatus.FAILED:
            return False
        if self == TaskStatus.FAILED:
            return target == TaskStatus.PENDING
        # PENDING 可以转到任何非终止状态
        if self == TaskStatus.PENDING:
            return target != TaskStatus.PENDING
        # SEARCHING 只能转到 DOWNLOADING 或终止状态
        if self == TaskStatus.SEARCHING:
            return target in (TaskStatus.DOWNLOADING, TaskStatus.FAILED,
                              TaskStatus.CANCELLED, TaskStatus.SKIPPED)
        # DOWNLOADING 只能转到终止状态
        if self == TaskStatus.DOWNLOADING:
            return target.is_terminal()
        return False


# 有效的状态转换图（用于快速检查）
_VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskStatus.SEARCHING, TaskStatus.SKIPPED, TaskStatus.CANCELLED,
    },
    TaskStatus.SEARCHING: {
        TaskStatus.DOWNLOADING, TaskStatus.FAILED,
        TaskStatus.CANCELLED, TaskStatus.SKIPPED,
    },
    TaskStatus.DOWNLOADING: {
        TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED,
    },
    # 终止状态不能转换
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: {TaskStatus.PENDING},  # 允许重试
    TaskStatus.CANCELLED: set(),
    TaskStatus.SKIPPED: set(),
}


@dataclass
class DownloadTask:
    """下载任务数据模型

    Attributes:
        video: 关联的视频文件
        subtitles: 已下载或待下载的字幕列表
        status: 当前任务状态
        error: 错误信息（失败时）
        progress: 下载进度（0-100）
        current_subtitle_index: 当前正在处理的字幕索引
        total_subtitles: 计划下载的字幕总数
        created_at: 任务创建时间戳
        started_at: 任务开始处理时间戳
        completed_at: 任务完成时间戳
        retry_count: 已重试次数
        max_retries: 最大重试次数
        log_messages: 任务日志消息列表
    """
    video: VideoFile
    subtitles: list[SubtitleInfo] = field(default_factory=list)
    status: str = "pending"
    error: str = ""
    progress: int = 0
    current_subtitle_index: int = 0
    total_subtitles: int = 0
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    retry_count: int = 0
    max_retries: int = 2
    log_messages: list[str] = field(default_factory=list)

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.total_subtitles == 0 and self.subtitles:
            self.total_subtitles = len(self.subtitles)
        # 确保 status 是有效的枚举值
        try:
            self._status_enum = TaskStatus.from_string(self.status)
        except Exception:
            self._status_enum = TaskStatus.PENDING
            self.status = "pending"

    # ── 状态管理 ──────────────────────────────────────────

    @property
    def status_enum(self) -> TaskStatus:
        return TaskStatus.from_string(self.status)

    def set_status(self, new_status: TaskStatus | str) -> None:
        """安全设置状态，附带合法性检查"""
        if isinstance(new_status, str):
            new_status = TaskStatus.from_string(new_status)

        current = TaskStatus.from_string(self.status)
        if current == new_status:
            return
        if not current.can_transition_to(new_status):
            raise ValueError(
                f"非法状态转换: {current.value} → {new_status.value}"
            )

        old_value = self.status
        self.status = new_status.value
        now = time.time()

        # 记录时间点
        if new_status == TaskStatus.SEARCHING or new_status == TaskStatus.DOWNLOADING:
            if self.started_at == 0.0:
                self.started_at = now
        if new_status.is_terminal():
            self.completed_at = now

        self._log(f"状态: {old_value} → {self.status}")

    def start_search(self) -> None:
        """开始搜索"""
        self.set_status(TaskStatus.SEARCHING)

    def start_download(self) -> None:
        """开始下载"""
        self.set_status(TaskStatus.DOWNLOADING)

    def mark_completed(self) -> None:
        """标记为完成"""
        self.progress = 100
        self.set_status(TaskStatus.COMPLETED)

    def mark_failed(self, error_msg: str) -> None:
        """标记为失败"""
        self.error = error_msg
        self._log(f"失败: {error_msg}")
        self.set_status(TaskStatus.FAILED)

    def mark_cancelled(self) -> None:
        """标记为取消"""
        self.set_status(TaskStatus.CANCELLED)

    def mark_skipped(self, reason: str = "") -> None:
        """标记为跳过"""
        if reason:
            self.error = reason
            self._log(f"跳过: {reason}")
        self.set_status(TaskStatus.SKIPPED)

    def can_retry(self) -> bool:
        """检查是否还可以重试"""
        return (self.status_enum == TaskStatus.FAILED
                and self.retry_count < self.max_retries)

    def retry(self) -> None:
        """重置状态以便重试"""
        if not self.can_retry():
            raise RuntimeError(f"已达到最大重试次数 ({self.max_retries})")
        self.retry_count += 1
        self.progress = 0
        self.error = ""
        self.current_subtitle_index = 0
        self._log(f"重试第 {self.retry_count} 次")
        self.set_status(TaskStatus.PENDING)

    # ── 进度管理 ──────────────────────────────────────────

    def update_progress(self, value: int) -> None:
        """更新进度（0-100）"""
        self.progress = max(0, min(100, value))
        if self.progress >= 100 and self.status_enum == TaskStatus.DOWNLOADING:
            self.mark_completed()

    def advance_subtitle(self) -> bool:
        """前进到下一个字幕，返回是否还有更多字幕"""
        self.current_subtitle_index += 1
        if self.current_subtitle_index >= self.total_subtitles:
            return False
        return True

    # ── 日志 ──────────────────────────────────────────────

    def _log(self, message: str) -> None:
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_messages.append(f"[{timestamp}] {message}")

    # ── 时间计算 ──────────────────────────────────────────

    @property
    def elapsed_time(self) -> float:
        """返回已消耗时间（秒）"""
        if self.started_at == 0.0:
            return 0.0
        end = self.completed_at if self.completed_at > 0 else time.time()
        return end - self.started_at

    @property
    def elapsed_time_str(self) -> str:
        """返回人类可读的耗时"""
        secs = int(self.elapsed_time)
        if secs < 60:
            return f"{secs}秒"
        minutes, seconds = divmod(secs, 60)
        if minutes < 60:
            return f"{minutes}分{seconds}秒"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}时{minutes}分{seconds}秒"

    # ── 查询 ──────────────────────────────────────────────

    @property
    def current_subtitle(self) -> Optional[SubtitleInfo]:
        """返回当前正在处理的字幕"""
        if 0 <= self.current_subtitle_index < len(self.subtitles):
            return self.subtitles[self.current_subtitle_index]
        return None

    @property
    def completed_count(self) -> int:
        """返回已完成的字幕数"""
        return min(self.current_subtitle_index, self.total_subtitles)

    @property
    def is_done(self) -> bool:
        """任务是否已完成（终止状态）"""
        return self.status_enum.is_terminal()

    @property
    def is_running(self) -> bool:
        """任务是否正在运行"""
        return self.status_enum.is_active()

    # ── 序列化 ────────────────────────────────────────────

    def to_dict(self) -> dict:
        """转为字典（用于持久化）"""
        return {
            "video": self.video.to_dict() if self.video else {},
            "subtitles": [s.to_dict() for s in self.subtitles],
            "status": self.status,
            "error": self.error,
            "progress": self.progress,
            "current_subtitle_index": self.current_subtitle_index,
            "total_subtitles": self.total_subtitles,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "elapsed": self.elapsed_time,
            "log_messages": self.log_messages,
        }

    def __str__(self) -> str:
        video_name = self.video.file_name if self.video else "未知"
        return (
            f"[{self.status_enum.display_name()}] {video_name} "
            f"({self.completed_count}/{self.total_subtitles})"
        )

    def __repr__(self) -> str:
        return (
            f"DownloadTask(video={self.video.file_name!r}, "
            f"status={self.status!r}, progress={self.progress})"
        )


@dataclass
class BatchProgress:
    """批量下载进度汇总"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    cancelled: int = 0
    running: int = 0

    @property
    def overall_progress(self) -> int:
        """总体进度百分比"""
        if self.total == 0:
            return 100
        done = self.completed + self.failed + self.skipped + self.cancelled
        return int(done / self.total * 100)

    @property
    def summary(self) -> str:
        """汇总文本"""
        parts = [f"共 {self.total} 部"]
        if self.completed:
            parts.append(f"✅ {self.completed} 完成")
        if self.failed:
            parts.append(f"⚠ {self.failed} 失败")
        if self.skipped:
            parts.append(f"⏭ {self.skipped} 跳过")
        if self.running:
            parts.append(f"⏳ {self.running} 进行中")
        return " | ".join(parts)

    @classmethod
    def from_tasks(cls, tasks: list[DownloadTask]) -> "BatchProgress":
        """从任务列表统计汇总"""
        stats = cls(total=len(tasks))
        for t in tasks:
            s = t.status_enum
            if s == TaskStatus.COMPLETED:
                stats.completed += 1
            elif s == TaskStatus.FAILED:
                stats.failed += 1
            elif s == TaskStatus.SKIPPED:
                stats.skipped += 1
            elif s == TaskStatus.CANCELLED:
                stats.cancelled += 1
            elif s.is_active():
                stats.running += 1
        return stats
