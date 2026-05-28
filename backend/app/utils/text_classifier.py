"""
动账文本分类工具

使用流程（等价于 Excel 公式 TEXTJOIN + REGEXP "[一-龟]+"）:
  1. extract_chinese(text) → 去除数字/标点/英文，只留中文
  2. 用提取后的纯中文文本，精确匹配数据库中的分类字典
  3. 不做模糊匹配，不做阈值匹配，其他情况一律返回 none

典型用法:
    from app.utils.text_classifier import classify_text, extract_chinese

    # 从数据库加载字典（超管维护）
    category_dict = {
        "小额打款": ["小额打款", "商家向消费者小额打款商品补偿"],
        "商家责任赔付": ["因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付"],
    }

    result = classify_text(
        "【因商家责任导致消费者申请售后，扣除商家相应金额进行运费赔付-订单693-售后单146-运单YT251】",
        category_dict,
    )
    # → ClassifyResult(
    #       text="【因...】",
    #       chinese_text="因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付订单售后单运单",
    #       category="商家责任赔付",
    #       matched_keyword="因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付",
    #       match_type="exact",
    #       match_score=100.0,
    #   )
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ============================================================
# 数据结构
# ============================================================


@dataclass
class ClassifyResult:
    """分类结果"""

    text: str = ""  # 原始文本
    chinese_text: str = ""  # 提取后的中文文本
    category: str | None = None  # 匹配到的分类
    matched_keyword: str | None = None  # 命中的关键词
    match_type: str = "none"  # exact / none
    match_score: float = 0.0  # 匹配分数（0~100）


# ============================================================
# 核心函数
# ============================================================


def extract_chinese(text: str) -> str:
    """
    提取文本中的中文字符。
    等价于 Excel 公式: TEXTJOIN(,FALSE,REGEXP($A1,"[一-龟]+"))

    范围：CJK 统一汉字基本区 U+4E00 ~ U+9FFF
    """
    return "".join(re.findall(r"[\u4e00-\u9fff]+", text))


def _build_sorted_index(
    category_dict: dict[str, list[str]],
) -> list[tuple[str, str]]:
    """将字典展开为 (keyword, category) 列表，按关键词长度降序排列。"""
    entries: list[tuple[str, str]] = []
    for category, keywords in category_dict.items():
        for kw in keywords:
            normalized_keyword = extract_chinese(kw)
            if normalized_keyword:
                entries.append((normalized_keyword, category))
    entries.sort(key=lambda x: len(x[0]), reverse=True)
    return entries


def _classify_exact(
    *,
    text: str,
    category_dict: dict[str, list[str]],
) -> ClassifyResult:
    result = ClassifyResult(text=text)
    result.chinese_text = extract_chinese(text)

    if not result.chinese_text or not category_dict:
        return result

    # ── 第一轮：精确匹配 ──
    for category, keywords in category_dict.items():
        for kw in keywords:
            normalized_keyword = extract_chinese(kw)
            if result.chinese_text == normalized_keyword:
                result.category = category
                result.matched_keyword = normalized_keyword
                result.match_type = "exact"
                result.match_score = 100.0
                return result

    return result


def classify_text(
    text: str,
    category_dict: dict[str, list[str]],
) -> ClassifyResult:
    """
    对单条文本进行分类。

    匹配策略：
      1. 精确匹配：提取中文后与字典关键词做 == 比较
      2. 其他情况一律返回 none

    Args:
        text:          原始文本（如动账备注，可含标点/数字/英文）
        category_dict: 分类字典 {"分类名": ["关键词1", "关键词2"]}

    Returns:
        ClassifyResult
    """
    return _classify_exact(text=text, category_dict=category_dict)


def classify_batch(
    texts: list[str],
    category_dict: dict[str, list[str]],
) -> list[ClassifyResult]:
    """批量分类。"""
    return [_classify_exact(text=text, category_dict=category_dict) for text in texts]
