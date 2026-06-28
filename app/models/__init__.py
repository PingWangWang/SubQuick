"""SubQuick 数据模型

提供核心业务对象的数据类和枚举。
"""

from app.models.video import (
    VideoFile,
    SubtitleStatus,
    VIDEO_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    SUBTITLE_KEYWORDS,
)
from app.models.subtitle import (
    SubtitleInfo,
    rank_subtitles,
    get_language_display_name,
    normalize_language_code,
    LANGUAGE_DISPLAY_NAMES,
)
from app.models.task import (
    DownloadTask,
    TaskStatus,
    BatchProgress,
)
from app.models.settings import (
    Settings,
    LanguagePriority,
    MatchingConfig,
    ProviderConfig,
    ProxyConfig,
    IgnoreList,
    UIConfig,
    VALID_VIDEO_FORMATS,
    VALID_THEMES,
    SUPPORTED_LANGUAGES,
)

__all__ = [
    # video
    "VideoFile",
    "SubtitleStatus",
    "VIDEO_EXTENSIONS",
    "SUBTITLE_EXTENSIONS",
    "SUBTITLE_KEYWORDS",
    # subtitle
    "SubtitleInfo",
    "rank_subtitles",
    "get_language_display_name",
    "normalize_language_code",
    "LANGUAGE_DISPLAY_NAMES",
    # task
    "DownloadTask",
    "TaskStatus",
    "BatchProgress",
    # settings
    "Settings",
    "LanguagePriority",
    "MatchingConfig",
    "ProviderConfig",
    "ProxyConfig",
    "IgnoreList",
    "UIConfig",
    "VALID_VIDEO_FORMATS",
    "VALID_THEMES",
    "SUPPORTED_LANGUAGES",
]
