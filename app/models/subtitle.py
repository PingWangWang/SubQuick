"""字幕信息数据模型

提供 SubtitleInfo 数据类，包含字幕元数据、语言映射、
评分排序、序列化方法。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ISO 639-1 语言代码 → 中文显示名映射
LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "zh": "简体中文",
    "zh-cn": "简体中文",
    "zh-tw": "繁体中文",
    "zh-hk": "繁体中文（香港）",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "pt": "Português",
    "pt-br": "Português (Brasil)",
    "ru": "Русский",
    "it": "Italiano",
    "ar": "العربية",
    "tr": "Türkçe",
    "vi": "Tiếng Việt",
    "th": "ภาษาไทย",
    "id": "Bahasa Indonesia",
    "ms": "Bahasa Melayu",
    "nl": "Nederlands",
    "pl": "Polski",
    "sv": "Svenska",
    "da": "Dansk",
    "fi": "Suomi",
    "nb": "Norsk Bokmål",
    "cs": "Čeština",
    "hu": "Magyar",
    "ro": "Română",
    "el": "Ελληνικά",
    "he": "עברית",
    "hi": "हिन्दी",
}

# 语言置信度评分（用于自动选择时的权重加成）
LANGUAGE_SCORE_BOOST: dict[str, float] = {
    "zh": 10.0,
    "zh-cn": 10.0,
    "zh-tw": 9.0,
    "en": 8.0,
    "ja": 6.0,
    "ko": 5.0,
}


def normalize_language_code(code: str) -> str:
    """规范化语言代码，如 'zh-CN' → 'zh-cn'"""
    return code.strip().lower().replace("_", "-").replace(" ", "")


def get_language_display_name(code: str) -> str:
    """获取语言代码的显示名称"""
    normalized = normalize_language_code(code)
    # 精确匹配
    if normalized in LANGUAGE_DISPLAY_NAMES:
        return LANGUAGE_DISPLAY_NAMES[normalized]
    # 取前两位模糊匹配
    short = normalized[:2]
    if short in LANGUAGE_DISPLAY_NAMES:
        return LANGUAGE_DISPLAY_NAMES[short]
    return code


def is_chinese_language(code: str) -> bool:
    """判断是否为中文语言代码"""
    normalized = normalize_language_code(code)
    return normalized.startswith("zh")


def is_english_language(code: str) -> bool:
    """判断是否为英文语言代码"""
    return normalize_language_code(code).startswith("en")


@dataclass
class SubtitleInfo:
    """字幕信息数据模型

    Attributes:
        provider: 字幕源标识（如 "opensubtitles"）
        subtitle_id: 字幕在源中的唯一 ID
        language: 语言代码（ISO 639-1）
        file_name: 字幕文件名
        score: 匹配评分（0-10）
        download_url: 下载链接
        uploader: 上传者
        upload_date: 上传日期
        downloads_count: 下载次数
        fps: 帧率（字幕可能关联的帧率）
        format: 字幕格式（srt/ass/ssa/sub）
        hearing_impaired: 是否为听力障碍辅助字幕
        utf8_encoded: 是否 UTF-8 编码
        cds: 字幕对应的 CD 数
    """
    provider: str
    subtitle_id: str
    language: str = ""
    file_name: str = ""
    score: float = 0.0
    download_url: str = ""
    uploader: str = ""
    upload_date: str = ""
    downloads_count: int = 0
    fps: str = ""
    format: str = ""
    hearing_impaired: bool = False
    utf8_encoded: bool = True
    cds: int = 1
    _extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.language:
            self.language = normalize_language_code(self.language)
        if not self.format and self.file_name:
            ext = self.file_name.rsplit(".", 1)[-1].lower()
            if ext in ("srt", "ass", "ssa", "sub", "vtt", "idx"):
                self.format = ext
        if isinstance(self.score, str):
            try:
                self.score = float(self.score)
            except (ValueError, TypeError):
                self.score = 0.0
        if isinstance(self.downloads_count, str):
            try:
                self.downloads_count = int(self.downloads_count)
            except (ValueError, TypeError):
                self.downloads_count = 0

    # ── 属性 ──────────────────────────────────────────────

    @property
    def language_display(self) -> str:
        """返回语言的显示名称"""
        return get_language_display_name(self.language)

    @property
    def language_short(self) -> str:
        """返回语言代码的前两位"""
        return self.language[:2] if self.language else ""

    @property
    def is_chinese(self) -> bool:
        return is_chinese_language(self.language)

    @property
    def is_english(self) -> bool:
        return is_english_language(self.language)

    @property
    def format_upper(self) -> str:
        """返回大写的格式名"""
        return self.format.upper() if self.format else ""

    @property
    def adjusted_score(self) -> float:
        """返回调整后的评分（基础评分 + 语言权重加成）"""
        boost = LANGUAGE_SCORE_BOOST.get(self.language, 0)
        short = self.language_short
        if short and short != self.language:
            boost = max(boost, LANGUAGE_SCORE_BOOST.get(short, 0))
        return self.score + boost

    @property
    def is_valid(self) -> bool:
        """判断字幕信息是否有效"""
        return bool(self.provider and self.subtitle_id)

    # ── 序列化 ────────────────────────────────────────────

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "provider": self.provider,
            "subtitle_id": self.subtitle_id,
            "language": self.language,
            "language_display": self.language_display,
            "file_name": self.file_name,
            "score": self.score,
            "adjusted_score": self.adjusted_score,
            "download_url": self.download_url,
            "uploader": self.uploader,
            "upload_date": self.upload_date,
            "downloads_count": self.downloads_count,
            "format": self.format,
            "hearing_impaired": self.hearing_impaired,
            "utf8_encoded": self.utf8_encoded,
            "cds": self.cds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SubtitleInfo":
        """从字典创建实例"""
        return cls(
            provider=data.get("provider", ""),
            subtitle_id=str(data.get("subtitle_id", "")),
            language=data.get("language", ""),
            file_name=data.get("file_name", ""),
            score=float(data.get("score", 0)),
            download_url=data.get("download_url", ""),
            uploader=data.get("uploader", ""),
            upload_date=data.get("upload_date", ""),
            downloads_count=int(data.get("downloads_count", 0)),
            format=data.get("format", ""),
            hearing_impaired=bool(data.get("hearing_impaired", False)),
            utf8_encoded=bool(data.get("utf8_encoded", True)),
            cds=int(data.get("cds", 1)),
            _extra={k: v for k, v in data.items()
                    if k not in ("provider", "subtitle_id", "language", "file_name",
                                 "score", "download_url", "uploader", "upload_date",
                                 "downloads_count", "format", "hearing_impaired",
                                 "utf8_encoded", "cds")},
        )

    def __str__(self) -> str:
        return f"[{self.language_display}] {self.file_name} (评分: {self.adjusted_score:.1f})"

    def __repr__(self) -> str:
        return (
            f"SubtitleInfo(provider={self.provider!r}, id={self.subtitle_id!r}, "
            f"lang={self.language!r}, score={self.score})"
        )


def rank_subtitles(
    subtitles: list[SubtitleInfo],
    language_priority: Optional[list[str]] = None,
    max_count: int = 5,
) -> list[SubtitleInfo]:
    """对字幕列表按语言优先级和评分排序

    Args:
        subtitles: 字幕候选列表
        language_priority: 语言优先级列表，如 ["zh", "en"]
        max_count: 返回的最大数量

    Returns:
        排序后的字幕列表（高优先级在前）
    """
    if not subtitles:
        return []

    priority = language_priority or ["zh", "en"]

    def sort_key(sub: SubtitleInfo) -> tuple:
        lang = sub.language_short
        # 第一优先级：语言在优先级列表中的位置
        try:
            lang_rank = priority.index(lang) if lang in priority else len(priority)
        except ValueError:
            lang_rank = len(priority)
        # 第二优先级：调整后评分（降序）
        score = -sub.adjusted_score
        # 第三优先级：下载次数（降序）
        downloads = -sub.downloads_count
        return (lang_rank, score, downloads)

    sorted_list = sorted(subtitles, key=sort_key)
    return sorted_list[:max_count]
