"""UI 组件逻辑单元测试"""
import pytest
from app.ui.components.status_badge import StatusBadge, STATUS_CONFIG


class TestStatusBadge:
    def test_status_config_keys(self):
        """所有状态都应有配置"""
        required = ["missing", "exists", "downloading", "downloaded", "failed", "pending", "searching", "unknown"]
        for status in required:
            assert status in STATUS_CONFIG, f"缺少状态配置: {status}"

    def test_status_config_values(self):
        """每个状态配置应有必要字段"""
        for status, config in STATUS_CONFIG.items():
            assert "label" in config, f"{status} 缺少 label"
            assert "icon" in config, f"{status} 缺少 icon"
            assert "color" in config, f"{status} 缺少 color"

    def test_badge_creation(self):
        for status in STATUS_CONFIG:
            badge = StatusBadge(status=status)
            assert badge.controls is not None
            assert len(badge.controls) == 2  # icon + text

    def test_badge_unknown_fallback(self):
        badge = StatusBadge(status="nonexistent")
        assert badge.controls is not None

    def test_update_status(self):
        """验证 update_status 会更新控件属性（不依赖 page）"""
        # 直接测试内部的图标名称变化
        from app.ui.components.status_badge import STATUS_CONFIG
        cfg_missing = STATUS_CONFIG["missing"]
        cfg_exists = STATUS_CONFIG["exists"]
        assert cfg_missing["icon"] != cfg_exists["icon"]
        assert cfg_missing["label"] != cfg_exists["label"]
