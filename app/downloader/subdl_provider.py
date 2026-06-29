"""subdl 字幕库适配器

subdl 封装了 OpenSubtitles、Shooter、Subscene 等多平台搜索。
安装：pip install subdl 或将 .whl 放入 plugins/ 目录。
"""

from __future__ import annotations

import importlib
import os
from typing import Optional

from app.downloader.base import (
    BaseProvider,
    SearchParams,
    SearchResult,
    SearchResultItem,
)

# 尝试导入 subdl
_SUBDL_AVAILABLE = False
_subdl = None
try:
    _subdl = importlib.import_module("subdl")
    _SUBDL_AVAILABLE = True
except ImportError:
    pass


class SubdlError(Exception):
    pass


class SubdlProvider(BaseProvider):
    """subdl 字幕库适配器"""

    def __init__(
        self,
        api_key: str = "",
        timeout: int = 30,
        **kwargs,
    ):
        super().__init__(api_key=api_key, timeout=timeout)

    @property
    def provider_name(self) -> str:
        return "subdl"

    @property
    def available(self) -> bool:
        return _SUBDL_AVAILABLE

    def search(self, params: SearchParams) -> SearchResult:
        if not _SUBDL_AVAILABLE:
            return SearchResult(
                provider=self.provider_name,
                error="subdl 库未安装。请将 subdl .whl 放入 plugins/ 目录，或运行: pip install subdl",
            )
        if not params.is_valid:
            return SearchResult(provider=self.provider_name, error="搜索参数无效")
        try:
            # subdl 搜索接口：subdl.search(query, languages=None)
            query = params.query or params.file_name or ""
            languages = params.languages or ["zh", "en"]
            results = _subdl.search(query, languages=languages)
            items = []
            for idx, item in enumerate(results or []):
                sid = getattr(item, "id", str(idx)) or str(idx)
                items.append(SearchResultItem(
                    subtitle_id=str(sid),
                    language=getattr(item, "lang", "zh"),
                    file_name=getattr(item, "filename", ""),
                    score=8.0 - idx * 0.5,
                    download_url=getattr(item, "url", ""),
                    format="srt",
                    raw_data={"subdl_item": str(item)},
                ))
            return SearchResult(
                provider=self.provider_name,
                items=items,
                total_count=len(items),
            )
        except Exception as e:
            return SearchResult(
                provider=self.provider_name,
                error=f"subdl 搜索失败: {e}",
            )

    def download(self, subtitle_id: str) -> tuple[bytes, str]:
        if not _SUBDL_AVAILABLE:
            raise SubdlError("subdl 库未安装")
        try:
            # subdl 下载接口：subdl.download(url) -> (content, filename)
            content, filename = _subdl.download(subtitle_id)
            return content, filename
        except Exception as e:
            raise SubdlError(f"subdl 下载失败: {e}")
