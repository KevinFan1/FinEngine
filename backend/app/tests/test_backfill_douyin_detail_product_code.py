import re

from app.utils.product_code import extract_product_code
from scripts.backfill_douyin_detail_product_code import SQL_PRODUCT_CODE_CANDIDATE_PATTERN


def test_backfill_candidate_pattern_matches_current_product_code_prefixes() -> None:
    pattern = re.compile(SQL_PRODUCT_CODE_CANDIDATE_PATTERN, re.IGNORECASE)

    assert pattern.search("【云上雅岚】流萤丨18K绿松手链-多样性发一件-XYGD3089540-B")
    assert pattern.search("【云上雅岚】清浅丨18K蜜蜡耳钩-多样性发一件-XYGD343005-D")
    assert pattern.search("【子楚专属】3 ZC00100027 S925银镶嵌和田玉戒指")
    assert pattern.search("【云上珠宝】小叶紫檀108佛珠多圈圆珠手串H200-6mm")


def test_backfill_uses_shared_product_code_rules() -> None:
    assert extract_product_code("【云上雅岚】流萤丨18K绿松手链-多样性发一件-XYGD3089540-B") == "XYGD3089540"
    assert extract_product_code("【云上雅岚】清浅丨18K蜜蜡耳钩-多样性发一件-XYGD343005-D") == "XYGD343005"
    assert extract_product_code("【云上叙】淡水珍珠项链-2.5mm V33535-F（商城）") == "V33535-F"
    assert extract_product_code("【云上叙】S925银淡水珍珠项链-3mm-V61416-M（甄选）") == "V61416-M"
