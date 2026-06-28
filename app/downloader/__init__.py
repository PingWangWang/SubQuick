"""SubQuick 下载模块"""
from app.downloader.base import BaseProvider, SearchParams, SearchResult, SearchResultItem
from app.downloader.opensubtitles import OpenSubtitlesProvider
from app.downloader.manager import DownloadManager, DownloadConfig

__all__ = [
    "BaseProvider", "SearchParams", "SearchResult", "SearchResultItem",
    "OpenSubtitlesProvider",
    "DownloadManager", "DownloadConfig",
]
