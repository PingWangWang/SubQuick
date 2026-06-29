"""扫描结果缓存：将上次扫描的视频列表保存到本地，重启后恢复"""

import json
import os
from pathlib import Path
from typing import Optional

from app.models.video import VideoFile


def _get_cache_dir() -> Path:
    """获取缓存目录"""
    if os.name == "nt":
        base = os.environ.get("APPDATA", "")
        if not base:
            base = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming")
    else:
        base = os.environ.get("XDG_CACHE_HOME", "")
        if not base:
            base = os.path.join(os.environ.get("HOME", ""), ".cache")
    cache_dir = Path(base) / "SubQuick"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def save_scan_cache(videos: list[VideoFile], scanned_dir: str) -> None:
    """保存扫描结果到本地缓存"""
    if not videos:
        return
    data = {
        "scanned_directory": scanned_dir,
        "videos": [v.to_dict() for v in videos],
    }
    cache_file = _get_cache_dir() / "scan_cache.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_scan_cache() -> tuple[list[VideoFile], str]:
    """从本地缓存加载上次扫描结果"""
    cache_file = _get_cache_dir() / "scan_cache.json"
    if not cache_file.exists():
        return [], ""
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        videos = [VideoFile.from_dict(v) for v in data.get("videos", [])]
        scanned_dir = data.get("scanned_directory", "")
        return videos, scanned_dir
    except Exception:
        return [], ""


def clear_scan_cache() -> None:
    """清除扫描缓存"""
    cache_file = _get_cache_dir() / "scan_cache.json"
    try:
        if cache_file.exists():
            cache_file.unlink()
    except Exception:
        pass
