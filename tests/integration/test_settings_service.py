"""SettingsService 集成测试"""
import pytest
import json
import os
from pathlib import Path
from app.services.settings_service import SettingsService
from app.models.settings import Settings


@pytest.fixture
def temp_config_dir(tmp_path):
    """创建临时配置目录，模拟 config/"""
    config_path = tmp_path / "config"
    config_path.mkdir()
    # 创建默认设置文件
    default = {
        "_version": "1.0.0",
        "video_directories": [],
        "video_formats": ["mp4", "mkv", "avi", "mov", "wmv"],
        "language_priority": {"primary": "zh", "fallback_chain": ["zh", "en"], "auto_fallback": True},
        "matching": {"max_subtitles_per_video": 3, "auto_select": True, "prefer_hearing_impaired": False},
        "subtitle_providers": {"opensubtitles": {"enabled": True, "api_key": "", "api_key_validated": False}},
        "proxy": {"enabled": False, "type": "http", "host": "", "port": 0, "username": "", "password": ""},
        "ignore_list": {"directories": [], "patterns": ["*sample*", "*trailer*"]},
        "ui": {"theme": "system", "language": "zh"},
        "first_run": True,
    }
    with open(config_path / "default_settings.json", "w", encoding="utf-8") as f:
        json.dump(default, f, indent=2)
    return tmp_path


class TestSettingsService:
    def test_default_settings(self, temp_config_dir):
        """测试首次加载返回默认设置"""
        service = SettingsService()
        # 覆写配置目录为临时路径
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        settings = service.load()
        assert isinstance(settings, Settings)
        assert settings.version == "1.0.0"
        assert settings.first_run
        assert settings.max_subtitles_per_video == 3

    def test_save_and_load(self, temp_config_dir):
        """测试保存和重新加载设置"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        # 修改并保存（首次保存，无备份文件）
        settings = service.load()
        settings.video_directories = [str(temp_config_dir)]
        settings.api_key = "my_api_key_123"
        settings.max_subtitles_per_video = 5
        settings.theme = "dark"
        service.save(settings)

        # 首次保存时无旧文件可备份
        assert service._config_file.exists()

        # 再次保存，此时应产生备份
        settings2 = service.load()
        settings2.theme = "light"
        service.save(settings2)

        # 验证备份文件存在
        assert service._backup_file.exists()

        # 重新加载验证
        settings3 = service.load()
        assert settings3.video_directories == [str(temp_config_dir)]

    def test_reset_to_defaults(self, temp_config_dir):
        """测试重置为默认值"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        # 先保存修改
        settings = service.load()
        settings.video_directories = [str(temp_config_dir)]
        service.save(settings)

        # 重置
        default_settings = service.reset_to_defaults()
        assert default_settings.video_directories == []
        assert default_settings.first_run

        # 重新加载验证重置
        reloaded = service.load()
        assert reloaded.video_directories == []

    def test_backup_on_save(self, temp_config_dir):
        """测试保存时自动备份"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        # 第一次保存（尚无旧文件，不会备份）
        settings = service.load()
        settings.video_directories = [str(temp_config_dir)]
        service.save(settings)

        # 第二次保存，产生备份
        settings.video_directories = [str(temp_config_dir / "movies")]
        service.save(settings)

        # 验证备份文件存在且内容为第一次保存的版本
        assert service._backup_file.exists()
        with open(service._backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        assert backup_data["video_directories"] == [str(temp_config_dir)]

    def test_invalid_settings_raises(self, temp_config_dir):
        """测试保存无效设置抛出异常"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        settings = service.load()
        # 绕过 setter 直接设置无效值（匹配数超出 1-5 范围）
        settings.matching.max_subtitles_per_video = 10
        with pytest.raises(ValueError, match="设置校验失败"):
            service.save(settings)

    def test_import_export_dict(self, temp_config_dir):
        """测试导入导出字典"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        data = {
            "_version": "1.0.0",
            "video_directories": ["/movies"],
            "video_formats": ["mp4", "mkv"],
            "matching": {"max_subtitles_per_video": 2},
            "ui": {"theme": "light", "language": "zh"},
            "first_run": False,
        }
        imported = service.import_from_dict(data)
        assert imported.video_directories == ["/movies"]
        assert imported.max_subtitles_per_video == 2
        assert imported.theme == "light"

        exported = service.export_to_dict(imported)
        assert exported["video_directories"] == ["/movies"]

    def test_get_setting_path(self, temp_config_dir):
        """测试获取设置文件路径"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        service._config_file = service._config_dir / "user_settings.json"
        service._backup_file = service._config_dir / "user_settings.backup.json"

        path = service.get_setting_path()
        assert "user_settings.json" in path

    def test_str(self, temp_config_dir):
        """测试字符串表示"""
        service = SettingsService()
        service._config_dir = temp_config_dir / "config"
        assert "SettingsService" in str(service)
