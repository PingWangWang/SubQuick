"""用户设置数据模型

提供 Settings 数据类，包含完整的用户配置字段、
值校验、序列化/反序列化、默认值合并等功能。
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field, fields as dataclass_fields
from typing import Any, Optional


# 支持的视频格式列表（全小写，不含点号）
VALID_VIDEO_FORMATS: list[str] = [
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm",
    "m4v", "mpg", "mpeg", "m2ts", "ts", "3gp",
]

# 有效的主题模式
VALID_THEMES: list[str] = ["system", "light", "dark"]

# 有效的代理类型
VALID_PROXY_TYPES: list[str] = ["http", "socks5", "socks4"]

# 支持的语言代码列表
SUPPORTED_LANGUAGES: list[str] = [
    "zh", "zh-cn", "zh-tw", "en", "ja", "ko",
    "fr", "de", "es", "pt", "pt-br", "ru",
    "it", "ar", "tr", "vi", "th",
]


@dataclass
class LanguagePriority:
    """语言优先级设置"""
    primary: str = "zh"
    fallback_chain: list[str] = field(default_factory=lambda: ["zh", "en"])
    auto_fallback: bool = True

    def __post_init__(self):
        self.validate()

    def validate(self) -> list[str]:
        """校验并返回错误列表"""
        errors: list[str] = []
        if self.primary and self.primary not in SUPPORTED_LANGUAGES:
            errors.append(f"不支持的首选语言: {self.primary}")
        for lang in self.fallback_chain:
            if lang not in SUPPORTED_LANGUAGES:
                errors.append(f"不支持的降级语言: {lang}")
        return errors

    def to_dict(self) -> dict:
        return {
            "primary": self.primary,
            "fallback_chain": self.fallback_chain,
            "auto_fallback": self.auto_fallback,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LanguagePriority":
        return cls(
            primary=data.get("primary", "zh"),
            fallback_chain=data.get("fallback_chain", ["zh", "en"]),
            auto_fallback=data.get("auto_fallback", True),
        )


@dataclass
class MatchingConfig:
    """字幕匹配设置"""
    max_subtitles_per_video: int = 3
    auto_select: bool = True
    prefer_hearing_impaired: bool = False

    def __post_init__(self):
        self.validate()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not (1 <= self.max_subtitles_per_video <= 5):
            errors.append(
                f"max_subtitles_per_video 必须介于 1-5 之间，当前值: {self.max_subtitles_per_video}"
            )
        return errors

    def to_dict(self) -> dict:
        return {
            "max_subtitles_per_video": self.max_subtitles_per_video,
            "auto_select": self.auto_select,
            "prefer_hearing_impaired": self.prefer_hearing_impaired,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MatchingConfig":
        return cls(
            max_subtitles_per_video=data.get("max_subtitles_per_video", 3),
            auto_select=data.get("auto_select", True),
            prefer_hearing_impaired=data.get("prefer_hearing_impaired", False),
        )


@dataclass
class ProviderConfig:
    """字幕源配置"""
    enabled: bool = True
    api_key: str = ""
    api_key_validated: bool = False

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "api_key": self.api_key,
            "api_key_validated": self.api_key_validated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfig":
        return cls(
            enabled=data.get("enabled", True),
            api_key=data.get("api_key", ""),
            api_key_validated=data.get("api_key_validated", False),
        )


@dataclass
class ProxyConfig:
    """代理设置"""
    enabled: bool = False
    type: str = "http"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    def __post_init__(self):
        self.validate()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.enabled:
            if self.type not in VALID_PROXY_TYPES:
                errors.append(f"不支持的代理类型: {self.type}")
            if not self.host:
                errors.append("代理已启用但未填写主机地址")
            if not (0 <= self.port <= 65535):
                errors.append(f"无效的代理端口: {self.port}")
        return errors

    @property
    def url(self) -> str:
        """返回代理 URL 字符串"""
        if not self.enabled or not self.host:
            return ""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        port_str = f":{self.port}" if self.port else ""
        return f"{self.type}://{auth}{self.host}{port_str}"

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "type": self.type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProxyConfig":
        return cls(
            enabled=data.get("enabled", False),
            type=data.get("type", "http"),
            host=data.get("host", ""),
            port=int(data.get("port", 0)),
            username=data.get("username", ""),
            password=data.get("password", ""),
        )


@dataclass
class IgnoreList:
    """忽略列表设置"""
    directories: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=lambda: ["*sample*", "*trailer*"])

    def matches(self, path_str: str) -> bool:
        """检查路径是否匹配忽略规则"""
        from fnmatch import fnmatch
        # 检查目录
        for d in self.directories:
            if d and path_str.startswith(d):
                return True
        # 检查文件名模式
        import os
        file_name = os.path.basename(path_str)
        for pattern in self.patterns:
            if fnmatch(file_name, pattern):
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "directories": self.directories,
            "patterns": self.patterns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IgnoreList":
        return cls(
            directories=data.get("directories", []),
            patterns=data.get("patterns", ["*sample*", "*trailer*"]),
        )


@dataclass
class UIConfig:
    """界面设置"""
    theme: str = "system"
    language: str = "zh"
    font_family: str = ""
    font_size: int = 14

    def __post_init__(self):
        self.validate()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.theme not in VALID_THEMES:
            errors.append(f"无效的主题模式: {self.theme}，有效值: {VALID_THEMES}")
        if not (8 <= self.font_size <= 32):
            errors.append(f"字号超出范围: {self.font_size}")
        return errors

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "language": self.language,
            "font_family": self.font_family,
            "font_size": self.font_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UIConfig":
        return cls(
            theme=data.get("theme", "system"),
            language=data.get("language", "zh"),
            font_family=data.get("font_family", ""),
            font_size=data.get("font_size", 14),
        )


@dataclass
class Settings:
    """完整的用户设置

    对应 config/default_settings.json 的全部字段。
    提供 from_dict / to_dict 用于 JSON 序列化。
    """
    # 基本设置
    version: str = "1.0.0"
    video_directories: list[str] = field(default_factory=list)
    video_formats: list[str] = field(
        default_factory=lambda: ["mp4", "mkv", "avi", "mov", "wmv"]
    )

    # 子配置
    language_priority: LanguagePriority = field(default_factory=LanguagePriority)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    subtitle_providers: dict[str, ProviderConfig] = field(default_factory=lambda: {
        "opensubtitles": ProviderConfig(),
    })
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    ignore_list: IgnoreList = field(default_factory=IgnoreList)
    ui: UIConfig = field(default_factory=UIConfig)

    # 运行状态
    first_run: bool = True

    # 内部字段（不序列化）
    _file_path: str = ""

    # ── 校验 ──────────────────────────────────────────────

    def validate_all(self) -> list[str]:
        """全面校验所有配置，返回错误列表"""
        errors: list[str] = []

        # 视频格式
        for fmt in self.video_formats:
            if fmt.lower() not in VALID_VIDEO_FORMATS:
                errors.append(f"不支持的视频格式: {fmt}")

        # 子配置的校验
        errors.extend(self.language_priority.validate())
        errors.extend(self.matching.validate())
        errors.extend(self.ui.validate())
        if self.proxy.enabled:
            errors.extend(self.proxy.validate())

        return errors

    def has_errors(self) -> bool:
        """快速检查是否有配置错误"""
        return len(self.validate_all()) > 0

    @staticmethod
    def _path_exists(p: str) -> bool:
        import os
        return os.path.isdir(p)

    # ── 序列化 ────────────────────────────────────────────

    def to_dict(self) -> dict:
        """转为扁平的 JSON 兼容字典"""
        return {
            "_version": self.version,
            "video_directories": self.video_directories,
            "video_formats": self.video_formats,
            "language_priority": self.language_priority.to_dict(),
            "matching": self.matching.to_dict(),
            "subtitle_providers": {
                name: provider.to_dict()
                for name, provider in self.subtitle_providers.items()
            },
            "proxy": self.proxy.to_dict(),
            "ignore_list": self.ignore_list.to_dict(),
            "ui": self.ui.to_dict(),
            "first_run": self.first_run,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """从 JSON 兼容字典创建设置实例"""
        return cls(
            version=data.get("_version", "1.0.0"),
            video_directories=data.get("video_directories", []),
            video_formats=data.get("video_formats", ["mp4", "mkv", "avi", "mov", "wmv"]),
            language_priority=LanguagePriority.from_dict(
                data.get("language_priority", {})
            ),
            matching=MatchingConfig.from_dict(
                data.get("matching", {})
            ),
            subtitle_providers={
                name: ProviderConfig.from_dict(cfg)
                for name, cfg in data.get("subtitle_providers", {}).items()
            } or {"opensubtitles": ProviderConfig()},
            proxy=ProxyConfig.from_dict(data.get("proxy", {})),
            ignore_list=IgnoreList.from_dict(data.get("ignore_list", {})),
            ui=UIConfig.from_dict(data.get("ui", {})),
            first_run=data.get("first_run", True),
        )

    @classmethod
    def default(cls) -> "Settings":
        """返回默认设置"""
        return cls()

    def merge_with_defaults(self) -> None:
        """用默认值补全缺失的字段（防止新增字段为空）"""
        defaults = self.default()

        # 简单字段
        if not self.video_formats:
            self.video_formats = defaults.video_formats

        # 语言优先级
        if not self.language_priority.primary:
            self.language_priority.primary = defaults.language_priority.primary
        if not self.language_priority.fallback_chain:
            self.language_priority.fallback_chain = defaults.language_priority.fallback_chain

        # 匹配设置
        if not (1 <= self.matching.max_subtitles_per_video <= 5):
            self.matching.max_subtitles_per_video = defaults.matching.max_subtitles_per_video

        # 字幕源
        if not self.subtitle_providers:
            self.subtitle_providers = defaults.subtitle_providers

        # UI
        if self.ui.theme not in VALID_THEMES:
            self.ui.theme = defaults.ui.theme

    # ── 便捷访问 ──────────────────────────────────────────

    @property
    def max_subtitles_per_video(self) -> int:
        return self.matching.max_subtitles_per_video

    @max_subtitles_per_video.setter
    def max_subtitles_per_video(self, value: int) -> None:
        self.matching.max_subtitles_per_video = max(1, min(5, value))

    @property
    def api_key(self) -> str:
        providers = self.subtitle_providers
        if "opensubtitles" in providers:
            return providers["opensubtitles"].api_key
        return ""

    @api_key.setter
    def api_key(self, value: str) -> None:
        if "opensubtitles" not in self.subtitle_providers:
            self.subtitle_providers["opensubtitles"] = ProviderConfig()
        self.subtitle_providers["opensubtitles"].api_key = value
        self.subtitle_providers["opensubtitles"].api_key_validated = False

    @property
    def theme(self) -> str:
        return self.ui.theme

    @theme.setter
    def theme(self, value: str) -> None:
        if value in VALID_THEMES:
            self.ui.theme = value

    def __str__(self) -> str:
        dirs = len(self.video_directories)
        return (
            f"Settings(dirs={dirs}, lang={self.language_priority.primary}, "
            f"max_sub={self.max_subtitles_per_video}, theme={self.theme})"
        )
