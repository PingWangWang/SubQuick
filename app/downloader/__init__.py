"""SubQuick 下载模块"""
from app.downloader.base import BaseProvider, SearchParams, SearchResult, SearchResultItem
from app.downloader.opensubtitles import OpenSubtitlesProvider
from app.downloader.shooter import ShooterProvider
from app.downloader.subdl_provider import SubdlProvider
from app.downloader.subliminal_provider import SubliminalProvider
from app.downloader.manager import DownloadManager, DownloadConfig
from app.downloader.registry import (
    register_provider,
    create_provider,
    create_enabled_providers,
    list_providers,
    init_plugins,
)

__all__ = [
    "BaseProvider", "SearchParams", "SearchResult", "SearchResultItem",
    "OpenSubtitlesProvider",
    "ShooterProvider",
    "SubdlProvider",
    "SubliminalProvider",
    "DownloadManager", "DownloadConfig",
    "register_provider",
    "create_provider",
    "create_enabled_providers",
    "list_providers",
    "init_plugins",
]
