"""文件格式过滤 + 忽略列表

提供视频文件格式白名单校验和忽略列表匹配功能。
"""

from __future__ import annotations

import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

from app.models.video import VIDEO_EXTENSIONS

# 默认支持的视频格式（小写，不含点号）
DEFAULT_VIDEO_FORMATS: list[str] = [
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm",
    "m4v", "mpg", "mpeg", "m2ts", "ts",
]

# 应排除的系统目录和隐藏目录
EXCLUDED_DIRECTORIES: set[str] = {
    "$recycle.bin", "system volume information",
    "recycler", "lost+found",
    ".git", ".svn", ".hg", ".idea", ".vscode",
    "__pycache__", "node_modules", ".venv", "venv",
}


def is_supported_format(file_path: Path, formats: Optional[list[str]] = None) -> bool:
    """检查文件扩展名是否在支持的视频格式列表中

    Args:
        file_path: 文件路径
        formats: 支持的格式列表（不含点号），默认使用 DEFAULT_VIDEO_FORMATS

    Returns:
        是否支持该格式
    """
    if formats is None:
        formats = DEFAULT_VIDEO_FORMATS
    ext = file_path.suffix.lower().lstrip(".")
    return ext in formats


def is_excluded_directory(dir_path: Path) -> bool:
    """检查目录是否应被排除（系统目录或隐藏目录）

    Args:
        dir_path: 目录路径

    Returns:
        是否应排除
    """
    name = dir_path.name.lower()
    # 隐藏目录（Unix 惯例）
    if name.startswith("."):
        return True
    # 已知排除目录
    if name in EXCLUDED_DIRECTORIES:
        return True
    return False


def matches_ignore_pattern(file_name: str, patterns: list[str]) -> bool:
    """检查文件名是否匹配忽略模式列表

    支持 fnmatch 通配符：* ? [seq] [!seq]

    Args:
        file_name: 文件名（含扩展名）
        patterns: 忽略模式列表，如 ["*sample*", "*trailer*"]

    Returns:
        是否匹配任一忽略模式
    """
    for pattern in patterns:
        if fnmatch(file_name.lower(), pattern.lower()):
            return True
    return False


def matches_ignore_directory(
    file_path: Path, ignore_dirs: list[str]
) -> bool:
    """检查文件路径是否位于忽略目录列表中

    Args:
        file_path: 文件完整路径
        ignore_dirs: 忽略目录路径列表

    Returns:
        是否位于忽略目录中
    """
    file_str = str(file_path).lower()
    for d in ignore_dirs:
        if not d:
            continue
        d_normalized = os.path.normpath(d).lower()
        if file_str.startswith(d_normalized):
            return True
    return False


class FileFilter:
    """文件过滤器

    组合视频格式白名单、忽略模式、忽略目录的过滤逻辑。
    """

    def __init__(
        self,
        video_formats: Optional[list[str]] = None,
        ignore_patterns: Optional[list[str]] = None,
        ignore_directories: Optional[list[str]] = None,
    ):
        self.video_formats = video_formats or DEFAULT_VIDEO_FORMATS
        self.ignore_patterns = ignore_patterns or []
        self.ignore_directories = ignore_directories or []

    def is_video_file(self, file_path: Path) -> bool:
        """判断是否为可接受的视频文件（格式 + 非忽略）

        Args:
            file_path: 文件路径

        Returns:
            是否应被纳入扫描
        """
        if not file_path.is_file():
            return False
        if not is_supported_format(file_path, self.video_formats):
            return False
        if matches_ignore_pattern(file_path.name, self.ignore_patterns):
            return False
        if matches_ignore_directory(file_path, self.ignore_directories):
            return False
        return True

    def should_scan_directory(self, dir_path: Path) -> bool:
        """判断是否应扫描该目录

        Args:
            dir_path: 目录路径

        Returns:
            是否应扫描
        """
        if not dir_path.is_dir():
            return False
        if is_excluded_directory(dir_path):
            return False
        return True

    def __repr__(self) -> str:
        return (
            f"FileFilter(formats={self.video_formats}, "
            f"patterns={self.ignore_patterns}, "
            f"dirs={len(self.ignore_directories)})"
        )
