"""SubQuick 日志配置

统一的日志系统，支持文件轮转、格式化输出、模块级日志器。
日志目录：%APPDATA%/SubQuick/logs/（生产）或 ./logs/（开发）
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


# 日志级别
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# 默认配置
DEFAULT_LOG_LEVEL = "debug"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_BACKUP_COUNT = 3
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_log_dir() -> Path:
    """获取日志目录路径"""
    if os.name == "nt":
        base = os.environ.get("APPDATA", "")
        if not base:
            base = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming")
    else:
        base = os.environ.get("XDG_DATA_HOME", "")
        if not base:
            base = os.path.join(os.environ.get("HOME", ""), ".local", "share")
    log_dir = Path(base) / "SubQuick" / "logs"
    return log_dir


def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    log_dir: Optional[Path] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    console_output: bool = True,
) -> logging.Logger:
    """配置全局日志系统

    Args:
        log_level: 日志级别名称
        log_dir: 日志目录，默认 %APPDATA%/SubQuick/logs/
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数
        console_output: 是否同时输出到控制台

    Returns:
        根日志器
    """
    level = LOG_LEVELS.get(log_level.lower(), logging.INFO)

    # 获取根日志器
    root_logger = logging.getLogger("subquick")
    root_logger.setLevel(level)

    # 清除已有的处理器（防止重复）
    root_logger.handlers.clear()

    # 创建日志目录
    if log_dir is None:
        log_dir = _get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    # 文件处理器（带轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        root_logger.addHandler(console_handler)

    # 全局异常捕获
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """全局未捕获异常处理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.critical(
            "未捕获异常",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = global_exception_handler

    root_logger.info(f"日志系统初始化完成: {log_file}")
    root_logger.info(f"日志级别: {log_level}")
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取模块级日志器

    Args:
        name: 模块名，通常使用 __name__

    Returns:
        日志器实例
    """
    return logging.getLogger(f"subquick.{name}")


# 默认日志配置（在模块导入时不会自动初始化）
_logger_initialized = False


def ensure_logging() -> logging.Logger:
    """确保日志系统已初始化（惰性初始化）"""
    global _logger_initialized
    if not _logger_initialized:
        logger = setup_logging()
        _logger_initialized = True
        return logger
    return logging.getLogger("subquick")
