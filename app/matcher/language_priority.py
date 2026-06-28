"""语言优先级与降级策略

管理用户首选语言的降级链条，判断给定的语言代码
在优先级链中的位置，用于字幕自动选择。
"""

from __future__ import annotations

from app.models.subtitle import normalize_language_code, is_chinese_language


# 默认降级链：简体中文 → 繁体中文 → English
DEFAULT_FALLBACK_CHAIN: list[str] = ["zh", "zh-tw", "en"]

# 语言族映射（同一语系视为可接受）
LANGUAGE_FAMILIES: dict[str, list[str]] = {
    "zh": ["zh", "zh-cn", "zh-tw", "zh-hk"],
    "en": ["en", "en-us", "en-gb", "en-au"],
    "ja": ["ja"],
    "ko": ["ko"],
    "fr": ["fr", "fr-fr", "fr-ca"],
    "de": ["de", "de-de"],
    "es": ["es", "es-es", "es-mx"],
    "pt": ["pt", "pt-br", "pt-pt"],
    "ru": ["ru"],
    "it": ["it"],
    "ar": ["ar"],
    "vi": ["vi"],
    "th": ["th"],
}


def get_language_family(code: str) -> str:
    """获取语言代码的语系（取前两位）

    Args:
        code: 语言代码，如 "zh-cn"

    Returns:
        语系代码，如 "zh"
    """
    return normalize_language_code(code)[:2]


def languages_match(a: str, b: str) -> bool:
    """判断两个语言代码是否属于同一语系

    Args:
        a: 语言代码 A
        b: 语言代码 B

    Returns:
        是否匹配
    """
    return get_language_family(a) == get_language_family(b)


def get_priority_rank(
    language: str,
    fallback_chain: list[str],
) -> int:
    """获取语言在优先级链中的排名（越小越优先）

    匹配逻辑：
    1. 精确匹配优先级链中的条目
    2. 匹配语系（同语系视为匹配）
    3. 不在链中则返回 len(chain)（最低优先级）

    Args:
        language: 语言代码
        fallback_chain: 降级链，如 ["zh", "en"]

    Returns:
        排名值，0 最高，越大越靠后
    """
    lang = normalize_language_code(language)

    # 精确匹配
    for idx, target in enumerate(fallback_chain):
        if normalize_language_code(target) == lang:
            return idx

    # 语系匹配
    for idx, target in enumerate(fallback_chain):
        if languages_match(lang, normalize_language_code(target)):
            return idx

    return len(fallback_chain)


def build_fallback_chain(
    primary: str,
    auto_chinese_fallback: bool = True,
) -> list[str]:
    """构建完整的降级链

    Args:
        primary: 首选语言代码
        auto_chinese_fallback: 是否自动添加中文作为第二降级

    Returns:
        降级链列表，如 ["ja", "zh", "en"]
    """
    chain: list[str] = [primary]

    if auto_chinese_fallback and not is_chinese_language(primary):
        # 首选非中文时，添加中文降级
        if "zh" not in chain:
            chain.append("zh")
        if "zh-tw" not in chain:
            chain.append("zh-tw")

    # 确保英文作为最后降级
    if "en" not in chain:
        chain.append("en")

    return chain
