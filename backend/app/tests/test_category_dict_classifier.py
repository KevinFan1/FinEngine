from app.tasks.processors.douyin import DouyinDongzhangStrategy
from app.utils.text_classifier import classify_text, extract_chinese


def test_classify_text_normalizes_input_and_returns_contains_match() -> None:
    category_dict = {
        "赔付": ["仲裁申诉通过打款"],
        "商家责任赔付": ["因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付"],
    }

    result = classify_text("【仲裁申诉通过打款-订单 123】", category_dict)

    assert result.chinese_text == "仲裁申诉通过打款订单"
    assert result.category == "赔付"
    assert result.matched_keyword == "仲裁申诉通过打款"
    assert result.match_type == "contains"


def test_classify_text_prefers_longest_contains_keyword() -> None:
    category_dict = {
        "赔付": ["赔付"],
        "商家责任赔付": ["因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付"],
    }

    result = classify_text(
        "【因商家责任导致消费者申请售后，扣除商家相应金额进行运费赔付-订单 123】",
        category_dict,
    )

    assert result.category == "商家责任赔付"
    assert result.matched_keyword == "因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付"
    assert result.match_type == "contains"


def test_classify_text_normalizes_dictionary_keywords() -> None:
    category_dict = {
        "赔付": ["【仲裁申诉通过打款】"],
    }

    result = classify_text("仲裁申诉通过打款", category_dict)

    assert result.category == "赔付"
    assert result.matched_keyword == "仲裁申诉通过打款"
    assert result.match_type == "exact"


def test_douyin_compensation_match_uses_canonical_chinese_text() -> None:
    beizhu = extract_chinese("【仲裁申诉通过打款-订单 123】")

    matched = DouyinDongzhangStrategy._match_compensation(
        beizhu,
        {"赔付": ["仲裁申诉通过打款"]},
    )

    assert matched == "赔付"
