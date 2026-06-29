"""字幕源提供者注册与选择器

管理所有可用 Provider 的注册、查询、实例化。
根据用户设置选择当前激活的字幕源。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from app.downloader.base import BaseProvider


# Provider 类注册表：name -> provider_class
_PROVIDER_CLASSES: dict[str, type] = {}


def register_provider(name: str, provider_class: type) -> None:
    """注册一个字幕源提供者类"""
    _PROVIDER_CLASSES[name] = provider_class


def get_provider_class(name: str) -> Optional[type]:
    """根据名称获取提供者类"""
    return _PROVIDER_CLASSES.get(name)


def list_providers() -> list[str]:
    """返回所有已注册的提供者名称列表"""
    return list(_PROVIDER_CLASSES.keys())


def create_provider(
    name: str,
    api_key: str = "",
    timeout: int = 30,
    proxy: Optional[dict] = None,
    **kwargs,
) -> Optional[BaseProvider]:
    """创建指定名称的 Provider 实例
    
    Args:
        name: Provider 名称
        api_key: API Key
        timeout: 请求超时
        proxy: 代理配置
        **kwargs: 传递给 Provider 构造函数的额外参数
        
    Returns:
        Provider 实例，如果名称不存在或不可用则返回 None
    """
    cls = get_provider_class(name)
    if cls is None:
        return None
    
    try:
        provider = cls(api_key=api_key, timeout=timeout, proxy=proxy, **kwargs)
        # 检查是否可用（如 subdl/subliminal 可能库未安装）
        if hasattr(provider, 'available') and not provider.available:
            return None
        return provider
    except Exception:
        return None


def create_enabled_providers(
    subtitle_providers: dict,
    active_provider: str,
    proxy: Optional[dict] = None,
) -> list[BaseProvider]:
    """根据用户设置创建当前启用的 Provider 列表
    
    Args:
        subtitle_providers: 用户设置中的 subtitle_providers 字典
        active_provider: 当前激活的 provider 名称
        proxy: 代理配置
        
    Returns:
        Provider 实例列表
    """
    providers = []
    
    # 先尝试创建激活的 provider
    if active_provider in subtitle_providers:
        cfg = subtitle_providers[active_provider]
        if cfg.get("enabled", True):
            p = create_provider(
                active_provider,
                api_key=cfg.get("api_key", ""),
                timeout=30,
                proxy=proxy,
            )
            if p is not None:
                providers.append(p)
    
    # 如果没有成功创建任何 provider，尝试所有 enabled 的
    if not providers:
        for name, cfg in subtitle_providers.items():
            if cfg.get("enabled", True):
                p = create_provider(
                    name,
                    api_key=cfg.get("api_key", ""),
                    timeout=30,
                    proxy=proxy,
                )
                if p is not None:
                    providers.append(p)
    
    return providers


def init_plugins(path: str = "plugins") -> None:
    """将 plugins 目录加入 sys.path，支持从该目录加载第三方库
    
    Args:
        path: plugins 目录路径（相对或绝对）
    """
    plugins_dir = Path(path)
    if plugins_dir.exists() and plugins_dir.is_dir():
        abs_path = str(plugins_dir.resolve())
        if abs_path not in sys.path:
            sys.path.insert(0, abs_path)


# ── 内置 Provider 注册 ─────────────────────────────────────

def _register_builtin_providers():
    """注册所有内置的 Provider 类"""
    # OpenSubtitles
    from app.downloader.opensubtitles import OpenSubtitlesProvider
    register_provider("opensubtitles", OpenSubtitlesProvider)
    
    # Shooter（伪射手网）
    from app.downloader.shooter import ShooterProvider
    register_provider("shooter", ShooterProvider)
    
    # subdl
    from app.downloader.subdl_provider import SubdlProvider
    register_provider("subdl", SubdlProvider)
    
    # subliminal
    from app.downloader.subliminal_provider import SubliminalProvider
    register_provider("subliminal", SubliminalProvider)


# 模块加载时自动注册
_register_builtin_providers()
