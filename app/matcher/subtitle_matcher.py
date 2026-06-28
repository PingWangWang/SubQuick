"""字幕自动选择算法

从候选字幕中按语言优先级和评分选择最优的字幕列表。
"""

from __future__ import annotations

from typing import Optional

from app.downloader.base import SearchResultItem
from app.matcher.language_priority import get_priority_rank


def select_best_subtitles(
    candidates: list[SearchResultItem],
    language_priority: Optional[list[str]] = None,
    max_count: int = 3,
) -> list[SearchResultItem]:
    """从候选字幕中选择最优的字幕列表

    选择策略：
    1. 按语言优先级分组（高优先级语言的字幕排在前面）
    2. 同语言内按评分降序排列
    3. 优先选择不同语言的字幕（避免重复语言）
    4. 总量不超过 max_count

    Args:
        candidates: 候选字幕列表
        language_priority: 语言优先级链，默认 ["zh", "en"]
        max_count: 最大选择数量（1-5）

    Returns:
        选择的最优字幕列表
    """
    if not candidates:
        return []

    priority = language_priority or ["zh", "en"]
    max_count = max(1, min(5, max_count))

    # 1. 按语言分组
    groups: dict[str, list[SearchResultItem]] = {}
    for sub in candidates:
        lang = (sub.language or "unknown")[:2]
        if lang not in groups:
            groups[lang] = []
        groups[lang].append(sub)

    # 2. 每组内按评分降序
    for lang in groups:
        groups[lang].sort(key=lambda s: -s.score)

    # 3. 按优先级排序语言组
    sorted_langs = sorted(
        groups.keys(),
        key=lambda lang: get_priority_rank(lang, priority),
    )

    # 4. 从每组取最优字幕，优先覆盖不同语言
    selected: list[SearchResultItem] = []
    lang_counts: dict[str, int] = {}

    # 第一轮：每组取最高分
    for lang in sorted_langs:
        if len(selected) >= max_count:
            break
        if groups[lang]:
            best = groups[lang][0]
            selected.append(best)
            lang_counts[lang] = 1

    # 第二轮：如果还有剩余名额，从高优先级组取更多
    if len(selected) < max_count:
        remaining = max_count - len(selected)
        for lang in sorted_langs:
            if remaining <= 0:
                break
            available = groups[lang][lang_counts.get(lang, 0):]
            for sub in available:
                if remaining <= 0:
                    break
                selected.append(sub)
                remaining -= 1

    return selected


def rank_candidates(
    candidates: list[SearchResultItem],
    language_priority: Optional[list[str]] = None,
) -> list[SearchResultItem]:
    """对候选字幕进行排序（不截断，按优先级+评分）

    Args:
        candidates: 候选字幕列表
        language_priority: 语言优先级链

    Returns:
        排序后的完整列表
    """
    if not candidates:
        return []

    priority = language_priority or ["zh", "en"]

    def sort_key(sub: SearchResultItem) -> tuple:
        lang_rank = get_priority_rank(sub.language or "", priority)
        # 评分降序
        score_rank = -sub.score
        # 下载次数降序
        download_rank = -sub.downloads_count
        return (lang_rank, score_rank, download_rank)

    return sorted(candidates, key=sort_key)
