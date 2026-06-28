"""下载任务数据模型"""

from dataclasses import dataclass, field
from app.models.video import VideoFile
from app.models.subtitle import SubtitleInfo


@dataclass
class DownloadTask:
    video: VideoFile
    subtitles: list[SubtitleInfo] = field(default_factory=list)
    status: str = "pending"  # "pending" | "searching" | "downloading" | "completed" | "failed"
    error: str = ""
