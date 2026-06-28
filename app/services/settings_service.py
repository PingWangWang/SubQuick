"""设置读写服务

负责用户设置的加载、保存、校验。
支持本地开发模式（项目根目录 config/）和生产模式（%APPDATA%/SubQuick/）。
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from app.models.settings import Settings
from app.utils.logging import get_logger


# 配置目录常量
CONFIG_DIR_NAME = "SubQuick"
CONFIG_FILE_NAME = "user_settings.json"
DEFAULT_CONFIG_FILE = "config/default_settings.json"
BACKUP_FILE_NAME = "user_settings.backup.json"


def _get_config_dir() -> Path:
    """获取用户配置目录（%APPDATA%/SubQuick/）"""
    if os.name == "nt":  # Windows
        base = os.environ.get("APPDATA", "")
        if not base:
            base = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming")
    elif os.name == "posix":
        base = os.environ.get("XDG_CONFIG_HOME", "")
        if not base:
            base = os.path.join(os.environ.get("HOME", ""), ".config")
    else:
        base = os.path.join(os.environ.get("HOME", ""), ".config")
    return Path(base) / CONFIG_DIR_NAME


def _get_project_root() -> Path:
    """获取项目根目录（main.py 所在目录）"""
    # 优先使用当前工作目录
    cwd = Path.cwd()
    if (cwd / "main.py").exists() or (cwd / "config").exists():
        return cwd
    # 回退：查找包含 main.py 的父目录
    for parent in [cwd] + list(cwd.parents):
        if (parent / "main.py").exists():
            return parent
    return cwd


def _ensure_dir(path: Path) -> None:
    """确保目录存在，不存在则创建"""
    path.mkdir(parents=True, exist_ok=True)


def _read_json_file(file_path: Path) -> dict:
    """读取 JSON 文件，返回字典"""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, PermissionError, OSError) as e:
        raise IOError(f"读取配置文件失败 {file_path}: {e}")


def _write_json_file(file_path: Path, data: dict) -> None:
    """写入 JSON 文件"""
    _ensure_dir(file_path.parent)
    try:
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except (PermissionError, OSError) as e:
        raise IOError(f"写入配置文件失败 {file_path}: {e}")


def _load_default_settings() -> dict:
    """加载默认设置文件"""
    # 尝试多个路径
    candidates = [
        Path(DEFAULT_CONFIG_FILE),
        _get_project_root() / DEFAULT_CONFIG_FILE,
        Path(__file__).parent.parent.parent / DEFAULT_CONFIG_FILE,
    ]
    for path in candidates:
        if path.exists():
            try:
                return _read_json_file(path)
            except IOError:
                continue
    # 没有默认设置文件，返回空字典
    return {}


class SettingsService:
    """设置读写服务

    管理用户设置的加载、保存、校验和恢复。

    Usage:
        service = SettingsService()
        settings = service.load()
        settings.max_subtitles_per_video = 5
        service.save(settings)
    """

    def __init__(self, use_appdata: bool = False):
        """
        Args:
            use_appdata: True 使用 %APPDATA%/SubQuick/ 存储，
                         False 使用项目目录 config/（开发模式）
        """
        self._use_appdata = use_appdata
        self._config_dir: Optional[Path] = None
        self._config_file: Optional[Path] = None
        self._backup_file: Optional[Path] = None
        self._init_paths()

    def _init_paths(self) -> None:
        """初始化文件路径"""
        if self._use_appdata:
            self._config_dir = _get_config_dir()
        else:
            self._config_dir = _get_project_root() / "config"
        self._config_file = self._config_dir / CONFIG_FILE_NAME
        self._backup_file = self._config_dir / BACKUP_FILE_NAME

    # ── 路径属性 ──────────────────────────────────────────

    @property
    def config_dir(self) -> str:
        """返回配置目录路径"""
        return str(self._config_dir) if self._config_dir else ""

    @property
    def config_file(self) -> str:
        """返回配置文件路径"""
        return str(self._config_file) if self._config_file else ""

    @property
    def use_appdata(self) -> bool:
        return self._use_appdata

    # ── 加载 ──────────────────────────────────────────────

    def load(self) -> Settings:
        """加载用户设置

        加载顺序：
        1. 尝试加载用户设置文件
        2. 如果不存在或损坏，尝试从备份恢复
        3. 如果都不可用，返回默认设置

        Returns:
            加载后的 Settings 实例
        """
        # 尝试加载用户设置
        if self._config_file and self._config_file.exists():
            try:
                data = _read_json_file(self._config_file)
                settings = Settings.from_dict(data)
                settings._file_path = str(self._config_file)
                settings.merge_with_defaults()
                return settings
            except (IOError, json.JSONDecodeError, Exception) as e:
                # 尝试从备份恢复
                restored = self._try_restore_from_backup()
                if restored:
                    return restored
                # 备份也不可用，返回默认设置
                settings = Settings.default()
                settings._file_path = str(self._config_file) if self._config_file else ""
                return settings

        # 用户设置文件不存在，尝试从备份恢复
        if self._backup_file and self._backup_file.exists():
            restored = self._try_restore_from_backup()
            if restored:
                return restored

        # 都不存在，返回默认设置
        settings = Settings.default()
        if self._config_file:
            settings._file_path = str(self._config_file)
        return settings

    def _try_restore_from_backup(self) -> Optional[Settings]:
        """尝试从备份文件恢复设置"""
        if not self._backup_file or not self._backup_file.exists():
            return None
        try:
            data = _read_json_file(self._backup_file)
            settings = Settings.from_dict(data)
            settings._file_path = str(self._config_file) if self._config_file else ""
            settings.merge_with_defaults()
            # 恢复成功后，写回主文件
            if self._config_file:
                self.save(settings)
            return settings
        except Exception:
            return None

    # ── 保存 ──────────────────────────────────────────────

    def save(self, settings: Settings) -> None:
        """保存用户设置

        保存前：
        1. 先备份现有文件
        2. 校验设置值
        3. 写入新文件

        Args:
            settings: 要保存的 Settings 实例

        Raises:
            IOError: 写入失败
            ValueError: 设置校验失败
        """
        # 校验
        errors = settings.validate_all()
        if errors:
            raise ValueError(f"设置校验失败:\n" + "\n".join(errors))

        # 确保目录存在
        if self._config_dir:
            _ensure_dir(self._config_dir)

        # 备份现有文件
        self._backup()

        # 写入新文件
        data = settings.to_dict()
        if self._config_file:
            _write_json_file(self._config_file, data)

    def _backup(self) -> None:
        """备份当前配置文件"""
        if not self._config_file or not self._config_file.exists():
            return
        try:
            shutil.copy2(str(self._config_file), str(self._backup_file))
        except (OSError, shutil.Error):
            pass  # 备份失败不影响主流程

    # ── 便捷方法 ──────────────────────────────────────────

    def reset_to_defaults(self) -> Settings:
        """重置为默认设置并保存"""
        settings = Settings.default()
        if self._config_file:
            settings._file_path = str(self._config_file)
        self.save(settings)
        return settings

    def export_to_dict(self, settings: Settings) -> dict:
        """导出设置为字典"""
        return settings.to_dict()

    def import_from_dict(self, data: dict) -> Settings:
        """从字典导入设置"""
        settings = Settings.from_dict(data)
        if self._config_file:
            settings._file_path = str(self._config_file)
        self.save(settings)
        return settings

    def get_setting_path(self) -> str:
        """返回设置文件的完整路径"""
        return str(self._config_file) if self._config_file else ""

    def __str__(self) -> str:
        return (
            f"SettingsService(file={self._config_file}, "
            f"use_appdata={self._use_appdata})"
        )
