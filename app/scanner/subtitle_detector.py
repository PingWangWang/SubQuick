"""字幕文件存在性检测

提供字幕文件查找和存在性检测功能。
支持多种字幕命名模式的匹配。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.models.video import SUBTITLE_EXTENSIONS


def find_subtitle_files(
    video_path: Path,
    search_dir: Optional[Path] = None,
) -> list[Path]:
    """查找与视频文件匹配的同名字幕文件

    匹配规则（按优先级）：
    1. 基础名完全匹配： video.srt
    2. 基础名 + 语言代码：video.chi.srt, video.eng.srt
    3. 基础名 + 语言标签：video.chs.srt, video.cht.srt
    4. 基础名 + 分隔符 + 语言：video - Chinese.srt

    Args:
        video_path: 视频文件路径
        search_dir: 搜索目录，默认为视频所在目录

    Returns:
        匹配的字幕文件路径列表（按文件名排序）
    """
    search_dir = search_dir or video_path.parent
    if not search_dir.exists():
        return []

    video_stem = video_path.stem
    video_stem_lower = video_stem.lower()
    matches: list[Path] = []

    for f in sorted(search_dir.iterdir()):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in SUBTITLE_EXTENSIONS:
            continue

        f_stem = f.stem
        f_stem_lower = f_stem.lower()

        # 规则1：完全匹配
        if f_stem_lower == video_stem_lower:
            matches.append(f)
            continue

        # 规则2：基础名.语言.srt  或 基础名-语言.srt
        if f_stem_lower.startswith(video_stem_lower):
            remainder = f_stem_lower[len(video_stem_lower):]
            if remainder.startswith(".") or remainder.startswith("-"):
                matches.append(f)
                continue

        # 规则3：语言.基础名.srt  (某些源的命名方式)
        if f_stem_lower.endswith(video_stem_lower):
            prefix = f_stem_lower[:-len(video_stem_lower)]
            if prefix.endswith(".") or prefix.endswith("-"):
                matches.append(f)
                continue

    return matches


def has_subtitle(video_path: Path, search_dir: Optional[Path] = None) -> bool:
    """检查视频文件是否有同名字幕

    Args:
        video_path: 视频文件路径
        search_dir: 搜索目录，默认为视频所在目录

    Returns:
        是否存在匹配的字幕文件
    """
    return len(find_subtitle_files(video_path, search_dir)) > 0


def count_subtitles(video_path: Path, search_dir: Optional[Path] = None) -> int:
    """统计匹配的字幕文件数量

    Args:
        video_path: 视频文件路径
        search_dir: 搜索目录，默认为视频所在目录

    Returns:
        匹配的字幕文件数量
    """
    return len(find_subtitle_files(video_path, search_dir))


def get_subtitle_filenames(
    video_path: Path, search_dir: Optional[Path] = None
) -> list[str]:
    """获取匹配的字幕文件名列表

    Args:
        video_path: 视频文件路径
        search_dir: 搜索目录，默认为视频所在目录

    Returns:
        匹配的字幕文件名列表
    """
    return [f.name for f in find_subtitle_files(video_path, search_dir)]


def detect_subtitles_for_videos(
    video_paths: list[Path], search_dir: Optional[Path] = None
) -> dict[Path, list[Path]]:
    """批量检测多个视频的字幕情况

    Args:
        video_paths: 视频文件路径列表
        search_dir: 搜索目录，默认为各自视频所在目录

    Returns:
        视频路径 → 匹配字幕文件列表 的映射
    """
    result: dict[Path, list[Path]] = {}
    for vp in video_paths:
        result[vp] = find_subtitle_files(vp, search_dir or vp.parent)
    return result
