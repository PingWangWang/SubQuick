"""Settings 数据模型单元测试"""
import pytest
from app.models.settings import (
    Settings,
    LanguagePriority,
    MatchingConfig,
    ProxyConfig,
    IgnoreList,
    UIConfig,
    VALID_THEMES,
)


class TestLanguagePriority:
    def test_default(self):
        lp = LanguagePriority()
        assert lp.primary == "zh"
        assert lp.fallback_chain == ["zh", "en"]
        assert lp.auto_fallback

    def test_to_from_dict(self):
        lp = LanguagePriority(primary="en", fallback_chain=["en", "zh"])
        d = lp.to_dict()
        restored = LanguagePriority.from_dict(d)
        assert restored.primary == "en"
        assert restored.fallback_chain == ["en", "zh"]

    def test_validation(self):
        lp = LanguagePriority(primary="invalid")
        errors = lp.validate()
        assert len(errors) > 0


class TestMatchingConfig:
    def test_default(self):
        mc = MatchingConfig()
        assert mc.max_subtitles_per_video == 3
        assert mc.auto_select

    def test_validation_valid(self):
        mc = MatchingConfig(max_subtitles_per_video=5)
        assert len(mc.validate()) == 0

    def test_validation_invalid(self):
        mc = MatchingConfig(max_subtitles_per_video=0)
        errors = mc.validate()
        assert len(errors) > 0

        mc = MatchingConfig(max_subtitles_per_video=10)
        errors = mc.validate()
        assert len(errors) > 0

    def test_to_from_dict(self):
        mc = MatchingConfig(max_subtitles_per_video=5, prefer_hearing_impaired=True)
        d = mc.to_dict()
        restored = MatchingConfig.from_dict(d)
        assert restored.max_subtitles_per_video == 5
        assert restored.prefer_hearing_impaired


class TestProxyConfig:
    def test_default(self):
        p = ProxyConfig()
        assert not p.enabled
        assert p.url == ""

    def test_url_generation(self):
        p = ProxyConfig(enabled=True, host="127.0.0.1", port=8080)
        assert "127.0.0.1:8080" in p.url

        p = ProxyConfig(enabled=True, host="proxy.example.com", port=3128,
                        username="user", password="pass")
        assert "user:pass@" in p.url

    def test_validation_enabled_without_host(self):
        p = ProxyConfig(enabled=True, host="", port=0)
        errors = p.validate()
        assert len(errors) > 0

    def test_to_from_dict(self):
        p = ProxyConfig(enabled=True, type="socks5", host="127.0.0.1", port=1080)
        d = p.to_dict()
        restored = ProxyConfig.from_dict(d)
        assert restored.enabled
        assert restored.type == "socks5"


class TestIgnoreList:
    def test_default(self):
        il = IgnoreList()
        assert "*sample*" in il.patterns

    def test_matches_directory(self):
        il = IgnoreList(directories=["/movies/samples"])
        assert il.matches("/movies/samples/test.mp4")
        assert not il.matches("/movies/main/test.mp4")

    def test_matches_pattern(self):
        il = IgnoreList(patterns=["*sample*"])
        assert il.matches("/movies/sample.mp4")
        assert il.matches("/movies/test_sample.mp4")
        assert not il.matches("/movies/movie.mp4")


class TestUIConfig:
    def test_default(self):
        ui = UIConfig()
        assert ui.theme == "system"

    def test_valid_themes(self):
        for theme in VALID_THEMES:
            ui = UIConfig(theme=theme)
            assert len(ui.validate()) == 0

    def test_invalid_theme(self):
        ui = UIConfig(theme="invalid")
        errors = ui.validate()
        assert len(errors) > 0


class TestSettings:
    def test_default(self):
        s = Settings.default()
        assert s.version == "1.0.0"
        assert s.video_formats == ["mp4", "mkv", "avi", "mov", "wmv"]
        assert s.first_run
        assert s.theme == "system"

    def test_from_dict(self):
        data = {
            "_version": "1.0.0",
            "video_directories": ["D:\\Movies"],
            "video_formats": ["mp4", "mkv"],
            "language_priority": {
                "primary": "en",
                "fallback_chain": ["en", "zh"],
            },
            "matching": {
                "max_subtitles_per_video": 5,
            },
            "subtitle_providers": {
                "opensubtitles": {
                    "enabled": True,
                    "api_key": "test_key",
                }
            },
            "ui": {
                "theme": "dark",
            },
            "first_run": False,
        }
        s = Settings.from_dict(data)
        assert s.version == "1.0.0"
        assert s.video_directories == ["D:\\Movies"]
        assert s.video_formats == ["mp4", "mkv"]
        assert s.language_priority.primary == "en"
        assert s.max_subtitles_per_video == 5
        assert s.api_key == "test_key"
        assert s.theme == "dark"
        assert not s.first_run

    def test_to_dict_roundtrip(self):
        original = Settings.default()
        original.video_directories = ["D:\\Movies"]
        original.api_key = "key123"
        original.max_subtitles_per_video = 4
        original.theme = "light"

        d = original.to_dict()
        restored = Settings.from_dict(d)

        assert restored.video_directories == ["D:\\Movies"]
        assert restored.api_key == "key123"
        assert restored.max_subtitles_per_video == 4
        assert restored.theme == "light"

    def test_merge_with_defaults(self):
        s = Settings(
            video_directories=["D:\\Movies"],
            video_formats=[],
            matching=MatchingConfig(max_subtitles_per_video=10),
        )
        s.merge_with_defaults()
        # 空格式用默认值填充
        assert s.video_formats == ["mp4", "mkv", "avi", "mov", "wmv"]
        # 超出范围的值被修正
        assert s.max_subtitles_per_video == 3

    def test_max_subtitles_setter(self):
        s = Settings.default()
        s.max_subtitles_per_video = 5
        assert s.max_subtitles_per_video == 5

        s.max_subtitles_per_video = 10  # 超出上限
        assert s.max_subtitles_per_video == 5

        s.max_subtitles_per_video = 0  # 低于下限
        assert s.max_subtitles_per_video == 1

    def test_api_key_setter(self):
        s = Settings.default()
        s.api_key = "my_key"
        assert s.api_key == "my_key"
        assert not s.subtitle_providers["opensubtitles"].api_key_validated

    def test_theme_setter(self):
        s = Settings.default()
        s.theme = "dark"
        assert s.theme == "dark"
        s.theme = "invalid"
        assert s.theme == "dark"  # 不变

    def test_has_errors(self):
        s = Settings.default()
        assert not s.has_errors()

    def test_validation_errors(self):
        s = Settings(
            video_formats=["invalid_format"],
            matching=MatchingConfig(max_subtitles_per_video=0),
        )
        errors = s.validate_all()
        assert len(errors) > 0

    def test_str(self):
        s = Settings.default()
        assert "Settings" in str(s)
