"""视频文件递归扫描

核心扫描引擎，递归遍历目录收集视频文件信息，
调用 FileFilter 过滤和 SubtitleDetector 检测字幕状态。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.models.video import VideoFile
from app.scanner.file_filter import FileFilter
from app.scanner.subtitle_detector import (
    find_subtitle_files,
    has_subtitle,
    count_subtitles,
    get_subtitle_filenames,
)
from app.utils.logging import get_logger


logger = get_logger("scanner")


# 进度回调类型：当前文件路径, 已处理数, 总数, 当前阶段描述
ProgressCallback = Callable[[str, int, int, str], None]


class ScanCancelled(Exception):
    """扫描被用户取消"""
    pass


@dataclass
class ScanResult:
    """扫描结果汇总"""
    total_files_found: int = 0
    video_files: list[VideoFile] = field(default_factory=list)
    skipped_dirs: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    scan_duration: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def total_videos(self) -> int:
        return len(self.video_files)

    @property
    def missing_subtitle_count(self) -> int:
        return sum(1 for v in self.video_files if v.subtitle_status == "missing")

    @property
    def existing_subtitle_count(self) -> int:
        return sum(1 for v in self.video_files if v.subtitle_status == "exists")

    def summary(self) -> str:
        return (
            f"扫描完成: 共发现 {self.total_files_found} 个文件, "
            f"{self.total_videos} 部视频 "
            f"(缺失字幕: {self.missing_subtitle_count}, "
            f"已有字幕: {self.existing_subtitle_count}), "
            f"耗时 {self.scan_duration:.1f}秒"
        )


def scan_directory(
    directory: str | Path,
    file_filter: Optional[FileFilter] = None,
    recursive: bool = True,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
    max_file_size: int = 0,
) -> ScanResult:
    """递归扫描目录，收集所有视频文件信息

    Args:
        directory: 要扫描的目录路径
        file_filter: 文件过滤器，默认使用 FileFilter()
        recursive: 是否递归扫描子目录
        progress_callback: 进度回调函数
        cancel_flag: 取消标志函数，返回 True 时取消扫描
        max_file_size: 最大文件大小（字节），0 表示不限制

    Returns:
        ScanResult 包含扫描结果汇总

    Raises:
        ScanCancelled: 扫描被用户取消
        FileNotFoundError: 目录不存在
        PermissionError: 无权限访问目录
    """
    scan_dir = Path(directory) if isinstance(directory, str) else directory
    if not scan_dir.exists():
        raise FileNotFoundError(f"目录不存在: {scan_dir}")
    if not scan_dir.is_dir():
        raise NotADirectoryError(f"路径不是目录: {scan_dir}")

    start_time = time.time()
    result = ScanResult()
    filter_obj = file_filter or FileFilter()

    logger.info(f"开始扫描目录: {scan_dir} (递归={recursive})")

    # 第一遍计数（用于进度百分比）
    total_estimate = 0
    if progress_callback:
        try:
            total_estimate = _count_files(scan_dir, recursive)
        except Exception:
            total_estimate = 0

    # 第二遍：实际扫描
    processed = 0
    errors: list[str] = []

    try:
        _do_scan(
            scan_dir=scan_dir,
            result=result,
            file_filter=filter_obj,
            recursive=recursive,
            progress_callback=progress_callback,
            cancel_flag=cancel_flag,
            max_file_size=max_file_size,
            processed=processed,
            total_estimate=total_estimate,
            errors=errors,
        )
    except ScanCancelled:
        raise
    except PermissionError as e:
        raise PermissionError(f"无权限访问目录: {e}")
    except Exception as e:
        raise RuntimeError(f"扫描过程发生错误: {e}")

    result.scan_duration = time.time() - start_time
    result.errors = errors
    logger.info(result.summary())
    return result


def _count_files(directory: Path, recursive: bool) -> int:
    """快速估算文件总数"""
    count = 0
    try:
        if recursive:
            for _ in directory.rglob("*"):
                count += 1
                if count > 100000:  # 上限10万，防止耗时过长
                    break
        else:
            for _ in directory.iterdir():
                count += 1
    except Exception:
        pass
    return count


def _do_scan(
    scan_dir: Path,
    result: ScanResult,
    file_filter: FileFilter,
    recursive: bool,
    progress_callback: Optional[ProgressCallback],
    cancel_flag: Optional[Callable[[], bool]],
    max_file_size: int,
    processed: int,
    total_estimate: int,
    errors: list[str],
) -> int:
    """递归执行扫描

    Returns:
        处理文件数
    """
    # 检查取消
    if cancel_flag and cancel_flag():
        raise ScanCancelled("用户取消扫描")

    try:
        entries = sorted(scan_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        result.skipped_dirs.append(str(scan_dir))
        return processed

    for entry in entries:
        # 检查取消
        if cancel_flag and cancel_flag():
            raise ScanCancelled("用户取消扫描")

        try:
            if entry.is_dir():
                if not file_filter.should_scan_directory(entry):
                    result.skipped_dirs.append(str(entry))
                    continue
                if recursive:
                    if progress_callback:
                        progress_callback(
                            str(entry), processed, total_estimate, "扫描"
                        )
                    processed = _do_scan(
                        entry, result, file_filter, recursive,
                        progress_callback, cancel_flag,
                        max_file_size, processed, total_estimate, errors,
                    )
            elif entry.is_file():
                processed += 1
                result.total_files_found += 1

                if progress_callback and processed % 10 == 0:
                    progress_callback(
                        str(entry), processed, total_estimate, "扫描"
                    )

                if not file_filter.is_video_file(entry):
                    continue

                # 文件大小过滤
                if max_file_size > 0 and entry.stat().st_size > max_file_size:
                    result.skipped_files.append(str(entry))
                    continue

                # 检测字幕状态
                sub_files = find_subtitle_files(entry)
                sub_count = len(sub_files)

                video = VideoFile(
                    path=entry,
                    file_name=entry.name,
                    extension=entry.suffix.lower(),
                    file_size=entry.stat().st_size,
                    duration=0.0,  # Phase 3 通过 ffprobe 补充
                    has_subtitle=sub_count > 0,
                    subtitle_status="exists" if sub_count > 0 else "missing",
                    subtitle_count=sub_count,
                    subtitle_files=[f.name for f in sub_files],
                )
                result.video_files.append(video)

        except PermissionError:
            result.skipped_files.append(str(entry))
            continue
        except Exception as e:
            errors.append(f"处理文件失败 {entry}: {e}")
            continue

    return processed
