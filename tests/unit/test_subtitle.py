"""SubtitleInfo 数据模型单元测试"""
import pytest
from app.models.subtitle import (
    SubtitleInfo,
    rank_subtitles,
    get_language_display_name,
    normalize_language_code,
)


class TestSubtitleInfo:
    def test_create_minimal(self):
        s = SubtitleInfo(provider="opensubtitles", subtitle_id="123")
        assert s.provider == "opensubtitles"
        assert s.subtitle_id == "123"
        assert s.score == 0.0
        assert s.is_valid

    def test_create_invalid(self):
        s = SubtitleInfo(provider="", subtitle_id="")
        assert not s.is_valid

    def test_language_display(self):
        s = SubtitleInfo(provider="test", subtitle_id="1", language="zh")
        assert s.language_display == "简体中文"
        assert s.language_short == "zh"

        s = SubtitleInfo(provider="test", subtitle_id="1", language="en")
        assert s.language_display == "English"

        s = SubtitleInfo(provider="test", subtitle_id="1", language="ja")
        assert s.language_display == "日本語"

    def test_unknown_language_display(self):
        s = SubtitleInfo(provider="test", subtitle_id="1", language="xx")
        assert s.language_display == "xx"

    def test_language_normalization(self):
        s = SubtitleInfo(provider="test", subtitle_id="1", language="zh-CN")
        assert s.language == "zh-cn"
        s = SubtitleInfo(provider="test", subtitle_id="1", language="ZH_TW")
        assert s.language == "zh-tw"

    def test_is_chinese(self):
        assert SubtitleInfo(provider="t", subtitle_id="1", language="zh").is_chinese
        assert SubtitleInfo(provider="t", subtitle_id="1", language="zh-cn").is_chinese
        assert not SubtitleInfo(provider="t", subtitle_id="1", language="en").is_chinese

    def test_is_english(self):
        assert SubtitleInfo(provider="t", subtitle_id="1", language="en").is_english
        assert not SubtitleInfo(provider="t", subtitle_id="1", language="zh").is_english

    def test_score_conversion(self):
        s = SubtitleInfo(provider="t", subtitle_id="1", score="8.5")
        assert s.score == 8.5

        s = SubtitleInfo(provider="t", subtitle_id="1", score="invalid")
        assert s.score == 0.0

    def test_adjusted_score(self):
        # 中文有加成
        s = SubtitleInfo(provider="t", subtitle_id="1", score=8.0, language="zh")
        assert s.adjusted_score == 18.0  # 8.0 + 10.0

        s = SubtitleInfo(provider="t", subtitle_id="1", score=8.0, language="en")
        assert s.adjusted_score == 16.0  # 8.0 + 8.0

        # 无加成的语言
        s = SubtitleInfo(provider="t", subtitle_id="1", score=8.0, language="fr")
        assert s.adjusted_score == 8.0

    def test_format_auto_detection(self):
        s = SubtitleInfo(provider="t", subtitle_id="1", file_name="sub.srt")
        assert s.format == "srt"
        assert s.format_upper == "SRT"

        s = SubtitleInfo(provider="t", subtitle_id="1")
        assert s.format == ""

    def test_to_dict(self):
        s = SubtitleInfo(
            provider="opensubtitles",
            subtitle_id="123456",
            language="zh",
            file_name="movie.chi.srt",
            score=9.2,
            download_url="https://example.com/sub.srt",
        )
        d = s.to_dict()
        assert d["provider"] == "opensubtitles"
        assert d["subtitle_id"] == "123456"
        assert d["language_display"] == "简体中文"
        assert d["adjusted_score"] == 19.2

    def test_from_dict(self):
        data = {
            "provider": "opensubtitles",
            "subtitle_id": "789",
            "language": "en",
            "score": 7.5,
            "downloads_count": "1500",
            "extra_field": "ignored",
        }
        s = SubtitleInfo.from_dict(data)
        assert s.provider == "opensubtitles"
        assert s.subtitle_id == "789"
        assert s.score == 7.5
        assert s.downloads_count == 1500

    def test_str_repr(self):
        s = SubtitleInfo(provider="test", subtitle_id="1", language="zh", score=9.0)
        assert "简体中文" in str(s)
        assert "SubtitleInfo" in repr(s)


class TestRankSubtitles:
    def test_empty_list(self):
        assert rank_subtitles([]) == []

    def test_single_subtitle(self):
        subs = [SubtitleInfo(provider="t", subtitle_id="1", language="zh", score=8.0)]
        result = rank_subtitles(subs)
        assert len(result) == 1

    def test_priority_sorting(self):
        """中文应该排在英文前面"""
        en = SubtitleInfo(provider="t", subtitle_id="1", language="en", score=9.0)
        zh = SubtitleInfo(provider="t", subtitle_id="2", language="zh", score=8.0)
        result = rank_subtitles([en, zh], language_priority=["zh", "en"])
        assert result[0].language == "zh"  # 中文优先

    def test_max_count(self):
        subs = [
            SubtitleInfo(provider="t", subtitle_id=str(i), language="en", score=5.0)
            for i in range(10)
        ]
        result = rank_subtitles(subs, max_count=3)
        assert len(result) == 3

    def test_score_within_same_language(self):
        """同语言内评分高的优先"""
        low = SubtitleInfo(provider="t", subtitle_id="1", language="en", score=5.0)
        high = SubtitleInfo(provider="t", subtitle_id="2", language="en", score=9.0)
        result = rank_subtitles([low, high], language_priority=["en"])
        assert result[0].subtitle_id == "2"


class TestHelpers:
    def test_get_language_display_name(self):
        assert get_language_display_name("zh") == "简体中文"
        assert get_language_display_name("en") == "English"
        assert get_language_display_name("ja") == "日本語"
        assert get_language_display_name("xx") == "xx"

    def test_get_language_display_with_region(self):
        assert get_language_display_name("zh-cn") == "简体中文"
        assert get_language_display_name("zh-tw") == "繁体中文"

    def test_normalize_language_code(self):
        assert normalize_language_code("zh-CN") == "zh-cn"
        assert normalize_language_code("ZH_TW") == "zh-tw"
        assert normalize_language_code("  En  ") == "en"
