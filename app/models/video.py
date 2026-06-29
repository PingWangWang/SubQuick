"""视频文件数据模型

提供 VideoFile 数据类，包含视频文件属性、字幕状态管理、
格式化输出和文件系统交互方法。
"""

from __future__ import annotations

import enum
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class SubtitleStatus(enum.Enum):
    """字幕状态枚举"""
    UNKNOWN = "unknown"
    MISSING = "missing"
    EXISTS = "exists"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    FAILED = "failed"

    @classmethod
    def from_string(cls, value: str) -> "SubtitleStatus":
        for member in cls:
            if member.value == value:
                return member
        return cls.UNKNOWN

    def display_name(self) -> str:
        names = {
            "unknown": "未知",
            "missing": "缺失",
            "exists": "已存在",
            "downloading": "下载中",
            "downloaded": "已下载",
            "failed": "失败",
        }
        return names.get(self.value, self.value)


# 常见视频格式扩展名集合（全小写）
VIDEO_EXTENSIONS: set[str] = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".m2ts", ".ts", ".3gp", ".ogv",
    ".divx", ".vob", ".rm", ".rmvb", ".asf",
}

# 字幕文件扩展名集合
SUBTITLE_EXTENSIONS: set[str] = {
    ".srt", ".ass", ".ssa", ".sub", ".vtt", ".idx",
}

# 常见的字幕关键词匹配模式（用于文件名识别）
SUBTITLE_KEYWORDS: list[str] = [
    "chs", "cht", "chi", "eng", "zh", "en", "ja", "kor",
    "sc", "tc", "gb", "big5",
    "default", "forced",
]


@dataclass
class VideoFile:
    """视频文件数据模型

    Attributes:
        path: 文件完整路径
        file_name: 文件名（含扩展名）
        extension: 文件扩展名（小写，含点号）
        file_size: 文件大小（字节）
        duration: 视频时长（秒）
        width: 视频宽度（像素），0 表示未知
        height: 视频高度（像素），0 表示未知
        has_subtitle: 是否存在同名字幕文件
        subtitle_status: 字幕状态
        subtitle_count: 已存在的同名字幕文件数量
        subtitle_files: 已存在的同名字幕文件名列表
    """
    path: Path
    file_name: str = ""
    extension: str = ""
    file_size: int = 0
    duration: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""       # 视频编码器 (h264, hevc, av1...)
    audio_codec: str = ""       # 音频编码器 (aac, ac3, dts...)
    audio_channels: int = 0     # 音频声道数
    frame_rate: float = 0.0     # 帧率
    bitrate: int = 0            # 总码率 (bps)
    has_subtitle: bool = False
    subtitle_status: str = "unknown"
    subtitle_count: int = 0
    subtitle_files: list[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后自动补全派生字段"""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if not self.file_name and self.path:
            self.file_name = self.path.name
        if not self.extension and self.path:
            self.extension = self.path.suffix.lower()
        if not self.file_size and self.path and self.path.exists():
            self.file_size = self.path.stat().st_size
        # 同步 has_subtitle 与 subtitle_status
        if self.has_subtitle and self.subtitle_status == "unknown":
            self.subtitle_status = "exists"
        elif not self.has_subtitle and self.subtitle_status == "unknown":
            self.subtitle_status = "missing"

    # ── 计算属性 ──────────────────────────────────────────

    @property
    def directory(self) -> str:
        """返回文件所在目录路径"""
        return str(self.path.parent) if self.path else ""

    @property
    def file_name_without_ext(self) -> str:
        """返回不带扩展名的文件名"""
        return self.path.stem if self.path else self.file_name

    @property
    def formatted_size(self) -> str:
        """返回人类可读的文件大小"""
        size = self.file_size
        if size == 0:
            return "未知"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def duration_str(self) -> str:
        """返回人类可读的时长（HH:MM:SS 或 MM:SS）"""
        if self.duration <= 0:
            return "未知"
        total_seconds = int(self.duration)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h{minutes:02d}m"
        return f"{minutes}m{seconds:02d}s"

    @property
    def resolution(self) -> str:
        """返回分辨率字符串，如 1920x1080"""
        if self.width > 0 and self.height > 0:
            return f"{self.width}x{self.height}"
        return ""

    @property
    def video_codec_label(self) -> str:
        """返回简短编码标签"""
        m = {"h264": "H.264", "hevc": "HEVC", "av1": "AV1", "mpeg4": "MPEG-4",
             "vp9": "VP9", "avc1": "H.264", "h265": "HEVC"}
        return m.get(self.video_codec.lower(), self.video_codec.upper()) if self.video_codec else ""

    @property
    def audio_codec_label(self) -> str:
        m = {"aac": "AAC", "ac3": "AC3", "dts": "DTS", "mp3": "MP3",
             "eac3": "EAC3", "opus": "Opus", "flac": "FLAC"}
        return m.get(self.audio_codec.lower(), self.audio_codec.upper()) if self.audio_codec else ""

    @property
    def audio_channels_str(self) -> str:
        if not self.audio_channels:
            return ""
        if self.audio_channels == 1:
            return "单声道"
        if self.audio_channels == 2:
            return "立体声"
        return f"{self.audio_channels}ch"

    @property
    def bitrate_str(self) -> str:
        if not self.bitrate:
            return ""
        kbps = self.bitrate // 1000
        return f"{kbps}kbps"

    @property
    def frame_rate_str(self) -> str:
        """返回帧率字符串"""
        return f"{self.frame_rate:.0f}fps" if self.frame_rate > 0 else ""

    @property
    def quality_label(self) -> str:
        """返回画质标签（根据高度）"""
        if self.height <= 0:
            return ""
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "2K"
        elif self.height >= 1080:
            return "1080P"
        elif self.height >= 720:
            return "720P"
        elif self.height >= 480:
            return "480P"
        else:
            return "SD"

    @property
    def status_icon(self) -> str:
        """返回字幕状态的图标标识"""
        icons = {
            "missing": "⚠",
            "exists": "✓",
            "downloading": "⏳",
            "downloaded": "✅",
            "failed": "✗",
            "unknown": "?",
        }
        return icons.get(self.subtitle_status, "?")

    @property
    def is_valid(self) -> bool:
        """判断视频文件是否有效（路径存在且是文件）"""
        return self.path is not None and self.path.exists() and self.path.is_file()

    # ── 工厂方法 ──────────────────────────────────────────

    @classmethod
    def from_path(cls, path: Path | str) -> "VideoFile":
        """从文件路径创建 VideoFile 实例，自动读取基础信息"""
        path = Path(path) if isinstance(path, str) else path
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if not path.is_file():
            raise ValueError(f"路径不是文件: {path}")

        return cls(
            path=path,
            file_name=path.name,
            extension=path.suffix.lower(),
            file_size=path.stat().st_size,
            duration=0.0,  # 需要后续通过 ffprobe 补充
        )

    @classmethod
    def is_video_file(cls, path: Path) -> bool:
        """判断文件是否为视频文件（按扩展名）"""
        return path.suffix.lower() in VIDEO_EXTENSIONS

    @classmethod
    def is_subtitle_file(cls, path: Path) -> bool:
        """判断文件是否为字幕文件（按扩展名）"""
        return path.suffix.lower() in SUBTITLE_EXTENSIONS

    @classmethod
    def find_matching_subtitles(cls, video_path: Path, scan_dir: Optional[Path] = None) -> list[Path]:
        """在指定目录（或视频同目录）中查找匹配的同名字幕文件

        匹配规则：
        - 基础名相同（不区分大小写）
        - 或基础名 + 语言关键词（如 .chs, .eng）
        """
        video_stem = video_path.stem.lower()
        search_dir = scan_dir or video_path.parent

        if not search_dir.exists():
            return []

        matches: list[Path] = []
        for f in sorted(search_dir.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() not in SUBTITLE_EXTENSIONS:
                continue
            f_stem = f.stem.lower()
            # 直接匹配
            if f_stem == video_stem:
                matches.append(f)
                continue
            # 视频名.语言.srt 模式
            if f_stem.startswith(video_stem):
                remainder = f_stem[len(video_stem):]
                if remainder.startswith("."):
                    matches.append(f)
        return matches

    # ── 序列化 ────────────────────────────────────────────

    def to_dict(self) -> dict:
        """转为字典（用于日志/序列化）"""
        return {
            "path": str(self.path) if self.path else "",
            "file_name": self.file_name,
            "extension": self.extension,
            "file_size": self.file_size,
            "formatted_size": self.formatted_size,
            "duration": self.duration,
            "duration_str": self.duration_str,
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "quality": self.quality_label,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "audio_channels": self.audio_channels,
            "frame_rate": self.frame_rate,
            "bitrate": self.bitrate,
            "has_subtitle": self.has_subtitle,
            "subtitle_status": self.subtitle_status,
            "subtitle_count": self.subtitle_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VideoFile":
        """从 to_dict() 输出的字典重建 VideoFile 实例"""
        from pathlib import Path
        return cls(
            path=Path(data.get("path", "")),
            file_name=data.get("file_name", ""),
            extension=data.get("extension", ""),
            file_size=data.get("file_size", 0),
            duration=data.get("duration", 0.0),
            width=data.get("width", 0),
            height=data.get("height", 0),
            has_subtitle=data.get("has_subtitle", False),
            subtitle_status=data.get("subtitle_status", "unknown"),
            subtitle_count=data.get("subtitle_count", 0),
        )

    def __str__(self) -> str:
        return f"{self.file_name} ({self.formatted_size}, {self.duration_str})"

    def __repr__(self) -> str:
        return (
            f"VideoFile(path={self.path!r}, file_name={self.file_name!r}, "
            f"size={self.formatted_size}, duration={self.duration_str}, "
            f"status={self.subtitle_status})"
        )
