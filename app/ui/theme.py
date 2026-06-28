"""SubQuick 应用主题与颜色常量

独立的主题模块，避免 app.py 与页面组件之间的循环导入。
"""

import flet as ft


class AppColors:
    """统一颜色常量"""
    PRIMARY = "#1565C0"
    PRIMARY_DARK = "#64B5F6"
    SUCCESS = "#2E7D32"
    SUCCESS_DARK = "#66BB6A"
    WARNING = "#E65100"
    WARNING_DARK = "#FFA726"
    ERROR = "#C62828"
    ERROR_DARK = "#EF5350"
    INFO = "#1565C0"
    INFO_DARK = "#42A5F5"
    BG_LIGHT = "#F5F5F5"
    BG_DARK = "#1E1E1E"
    CARD_LIGHT = "#FFFFFF"
    CARD_DARK = "#2D2D2D"
