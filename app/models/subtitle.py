"""字幕信息数据模型"""

from dataclasses import dataclass


@dataclass
class SubtitleInfo:
    provider: str
    subtitle_id: str
    language: str
    file_name: str
    score: float
    download_url: str = ""
