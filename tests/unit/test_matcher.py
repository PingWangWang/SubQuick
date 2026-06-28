"""Matcher 模块单元测试"""
import pytest
from app.downloader.base import SearchResultItem
from app.matcher.subtitle_matcher import select_best_subtitles, rank_candidates
from app.matcher.language_priority import (
    get_priority_rank,
    build_fallback_chain,
    languages_match,
    get_language_family,
)


@pytest.fixture
def sample_candidates():
    """创建一组测试用的候选字幕"""
    return [
        SearchResultItem(subtitle_id="1", language="en", score=9.0, downloads_count=5000),
        SearchResultItem(subtitle_id="2", language="zh", score=8.5, downloads_count=3000),
        SearchResultItem(subtitle_id="3", language="en", score=7.0, downloads_count=1000),
        SearchResultItem(subtitle_id="4", language="ja", score=8.0, downloads_count=200),
        SearchResultItem(subtitle_id="5", language="zh", score=6.5, downloads_count=500),
        SearchResultItem(subtitle_id="6", language="fr", score=9.5, downloads_count=100),
    ]


class TestSelectBestSubtitles:
    def test_empty(self):
        assert select_best_subtitles([]) == []

    def test_select_top_by_language(self, sample_candidates):
        """中文优先于英文"""
        selected = select_best_subtitles(
            sample_candidates,
            language_priority=["zh", "en"],
            max_count=2,
        )
        assert len(selected) == 2
        # 应该优先选择中文和英文
        langs = [s.language[:2] for s in selected]
        assert "zh" in langs
        assert "en" in langs

    def test_max_count_limit(self, sample_candidates):
        """测试数量限制"""
        selected = select_best_subtitles(sample_candidates, max_count=1)
        assert len(selected) == 1

    def test_max_count_clamping(self, sample_candidates):
        selected = select_best_subtitles(sample_candidates, max_count=0)
        assert len(selected) == 1  # 最小为1
        selected = select_best_subtitles(sample_candidates, max_count=10)
        assert len(selected) <= 6  # 总共只有6个

    def test_best_score_within_language(self):
        """同语言内选评分最高的"""
        subs = [
            SearchResultItem(subtitle_id="low", language="en", score=5.0),
            SearchResultItem(subtitle_id="high", language="en", score=9.0),
        ]
        selected = select_best_subtitles(subs, language_priority=["en"], max_count=1)
        assert selected[0].subtitle_id == "high"

    def test_prefer_different_languages(self):
        """优先覆盖不同语言"""
        subs = [
            SearchResultItem(subtitle_id="en1", language="en", score=9.0),
            SearchResultItem(subtitle_id="en2", language="en", score=8.0),
            SearchResultItem(subtitle_id="zh1", language="zh", score=7.0),
        ]
        selected = select_best_subtitles(subs, language_priority=["zh", "en"], max_count=2)
        langs = {s.language[:2] for s in selected}
        assert len(langs) == 2  # 中文和英文各一个


class TestRankCandidates:
    def test_empty(self):
        assert rank_candidates([]) == []

    def test_ranking_order(self, sample_candidates):
        """确认排序按语言优先级+评分"""
        ranked = rank_candidates(sample_candidates, language_priority=["zh", "en"])
        # 第一个应该是中文最高分
        assert ranked[0].language[:2] == "zh"
        assert ranked[0].subtitle_id == "2"

    def test_no_priority(self, sample_candidates):
        """未指定优先级时按评分排序"""
        ranked = rank_candidates(sample_candidates)
        assert len(ranked) == len(sample_candidates)


class TestLanguagePriority:
    def test_get_priority_rank_exact(self):
        rank = get_priority_rank("zh", ["zh", "en"])
        assert rank == 0

        rank = get_priority_rank("en", ["zh", "en"])
        assert rank == 1

    def test_get_priority_rank_family(self):
        rank = get_priority_rank("zh-cn", ["zh", "en"])
        assert rank == 0  # 属于 zh 语系

    def test_get_priority_rank_not_found(self):
        rank = get_priority_rank("ja", ["zh", "en"])
        assert rank == 2  # 不在链中

    def test_build_fallback_chain_chinese(self):
        chain = build_fallback_chain("zh")
        assert chain[0] == "zh"
        assert "en" in chain

    def test_build_fallback_chain_non_chinese(self):
        chain = build_fallback_chain("ja")
        assert chain[0] == "ja"
        assert "zh" in chain  # 自动添加中文降级
        assert "en" in chain

    def test_build_fallback_chain_without_auto(self):
        chain = build_fallback_chain("ja", auto_chinese_fallback=False)
        assert chain[0] == "ja"
        assert "zh" not in chain
        assert "en" in chain

    def test_languages_match(self):
        assert languages_match("zh-cn", "zh")
        assert languages_match("zh", "zh-tw")
        assert not languages_match("zh", "en")
        assert not languages_match("en", "ja")

    def test_get_language_family(self):
        assert get_language_family("zh-cn") == "zh"
        assert get_language_family("en-us") == "en"
        assert get_language_family("ja") == "ja"
