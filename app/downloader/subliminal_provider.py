"""subliminal 字幕库适配器

subliminal 是业界标准的 Python 字幕库，支持十余家字幕源，
自动识别电影/剧集，批量处理。
安装：pip install subliminal 或将 .whl 放入 plugins/ 目录。
"""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path
from typing import Optional

from app.downloader.base import (
    BaseProvider,
    SearchParams,
    SearchResult,
    SearchResultItem,
)

# 尝试导入 subliminal
_SUBLIMINAL_AVAILABLE = False
_subliminal = None
try:
    _subliminal = importlib.import_module("subliminal")
    _SUBLIMINAL_AVAILABLE = True
except ImportError:
    pass


class SubliminalError(Exception):
    pass


class SubliminalProvider(BaseProvider):
    """subliminal 字幕库适配器"""

    def __init__(
        self,
        api_key: str = "",
        timeout: int = 30,
        **kwargs,
    ):
        super().__init__(api_key=api_key, timeout=timeout)

    @property
    def provider_name(self) -> str:
        return "subliminal"

    @property
    def available(self) -> bool:
        return _SUBLIMINAL_AVAILABLE

    def search(self, params: SearchParams) -> SearchResult:
        if not _SUBLIMINAL_AVAILABLE:
            return SearchResult(
                provider=self.provider_name,
                error="subliminal 库未安装。请将相关 .whl 放入 plugins/ 目录，或运行: pip install subliminal",
            )
        if not params.is_valid:
            return SearchResult(provider=self.provider_name, error="搜索参数无效")
        try:
            from subliminal import Video
            from subliminal.core import search_subtitles

            # subliminal 需要 Video 对象
            video = Video(
                name=params.file_name or params.query or "unknown",
                source="Unknown",
            )
            if params.season > 0:
                video.season = params.season
            if params.episode > 0:
                video.episode = params.episode

            languages = params.languages or ["zh", "en"]
            subtitles = search_subtitles([video], languages=languages)

            items = []
            for idx, sub in enumerate(subtitles or []):
                items.append(SearchResultItem(
                    subtitle_id=getattr(sub, "id", str(idx)) or str(idx),
                    language=getattr(sub, "language", ""),
                    file_name=getattr(sub, "filename", ""),
                    score=getattr(sub, "score", 5.0),
                    download_url="",
                    format="srt",
                    raw_data={"subliminal_sub": str(sub)},
                ))
            return SearchResult(
                provider=self.provider_name,
                items=items,
                total_count=len(items),
            )
        except Exception as e:
            return SearchResult(
                provider=self.provider_name,
                error=f"subliminal 搜索失败: {e}",
            )

    def download(self, subtitle_id: str) -> tuple[bytes, str]:
        if not _SUBLIMINAL_AVAILABLE:
            raise SubliminalError("subliminal 库未安装")
        try:
            from subliminal import download_subtitles
            # subliminal 下载需要 Video 和 Subtitle 对象
            # subtitle_id 存储为序列化格式：provider:subtitle_id
            parts = subtitle_id.split(":", 1)
            if len(parts) == 2:
                provider_name, sid = parts
            else:
                provider_name, sid = "opensubtitles", subtitle_id

            # 创建一个临时 Video 对象用于下载
            from subliminal import Video
            video = Video(name="temp", source="Unknown")

            # 使用 subliminal 的下下载功能
            result = download_subtitles([video], providers=[provider_name])
            if result and result[0]:
                content = result[0].content
                filename = result[0].filename or f"subtitle_{sid}.srt"
                return content, filename
            raise SubliminalError("subliminal 未返回字幕内容")
        except SubliminalError:
            raise
        except Exception as e:
            raise SubliminalError(f"subliminal 下载失败: {e}")
