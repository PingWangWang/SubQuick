"""字幕下载器抽象基类和通用类型

定义 BaseProvider 抽象基类，所有字幕源适配器需实现此接口。
提供 SearchParams 和 SearchResult 等通用数据类型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchParams:
    """搜索参数"""
    query: str = ""                       # 文件名或关键词
    file_name: str = ""                   # 文件名（不含路径）
    file_hash: str = ""                   # 视频文件 hash
    file_size: int = 0                    # 文件大小（字节）
    imdb_id: str = ""                     # IMDb ID（可选）
    season: int = 0                       # 季号（剧集）
    episode: int = 0                      # 集号（剧集）
    languages: list[str] = field(default_factory=lambda: ["zh", "en"])
    max_count: int = 5                    # 每视频最大返回数

    @property
    def is_valid(self) -> bool:
        """至少需要文件名或 hash 才能搜索"""
        return bool(self.query or self.file_name or self.file_hash or self.imdb_id)


@dataclass
class SearchResultItem:
    """单个搜索结果项"""
    subtitle_id: str = ""
    language: str = ""
    file_name: str = ""
    score: float = 0.0
    download_url: str = ""
    uploader: str = ""
    upload_date: str = ""
    downloads_count: int = 0
    format: str = ""
    fps: str = ""
    cds: int = 1
    hearing_impaired: bool = False
    utf8_encoded: bool = True
    raw_data: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """搜索结果"""
    items: list[SearchResultItem] = field(default_factory=list)
    provider: str = ""
    total_count: int = 0
    error: str = ""

    @property
    def is_success(self) -> bool:
        return not self.error and len(self.items) > 0


class BaseProvider(ABC):
    """字幕源提供者基类

    所有字幕源适配器必须实现 search 和 download 方法。
    """

    def __init__(self, api_key: str = "", timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供者标识名，如 'opensubtitles'"""
        ...

    @abstractmethod
    def search(self, params: SearchParams) -> SearchResult:
        """搜索字幕

        Args:
            params: 搜索参数

        Returns:
            SearchResult 包含搜索结果列表
        """
        ...

    @abstractmethod
    def download(self, subtitle_id: str) -> tuple[bytes, str]:
        """下载字幕文件

        Args:
            subtitle_id: 字幕 ID

        Returns:
            (文件内容 bytes, 推荐文件名)
        """
        ...

    def validate_api_key(self) -> bool:
        """验证 API Key 是否有效

        Returns:
            True 有效, False 无效
        """
        return bool(self.api_key)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name})"
