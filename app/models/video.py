"""视频文件数据模型"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoFile:
    path: Path
    file_name: str
    extension: str
    file_size: int       # bytes
    duration: float      # seconds
    has_subtitle: bool
    subtitle_status: str = "unknown"  # "missing" | "exists" | "downloading" | "downloaded" | "failed"
