"""用户设置数据模型"""

from dataclasses import dataclass, field


@dataclass
class Settings:
    video_directories: list[str] = field(default_factory=list)
    video_formats: list[str] = field(default_factory=lambda: ["mp4", "mkv", "avi", "mov", "wmv"])
    primary_language: str = "zh"
    fallback_chain: list[str] = field(default_factory=lambda: ["zh", "en"])
    max_subtitles_per_video: int = 3
    theme: str = "system"  # "system" | "light" | "dark"
    proxy_enabled: bool = False
    proxy_type: str = "http"
    proxy_host: str = ""
    proxy_port: int = 0
