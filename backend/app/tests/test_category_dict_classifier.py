from app.tasks.processors.douyin import DouyinDongzhangStrategy
from app.utils.text_classifier import classify_text, extract_chinese


def test_classify_text_normalizes_input_and_returns_exact_match() -> None:
    category_dict = {
        "赔付": ["仲裁申诉通过打款"],
        "商家责任赔付": ["因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付"],
    }

    result = classify_text("【仲裁申诉通过打款-订单 123】", category_dict)

    assert result.chinese_text == "仲裁申诉通过打款订单"
    assert result.category is None
    assert result.matched_keyword is None
    assert result.match_type == "none"
    assert result.match_score == 0.0


def test_classify_text_normalizes_dictionary_keywords() -> None:
    category_dict = {
        "赔付": ["【仲裁申诉通过打款】"],
    }

    result = classify_text("仲裁申诉通过打款", category_dict)

    assert result.category == "赔付"
    assert result.matched_keyword == "仲裁申诉通过打款"
    assert result.match_type == "exact"
    assert result.match_score == 100.0


def test_douyin_compensation_match_uses_canonical_chinese_text() -> None:
    beizhu = extract_chinese("【仲裁申诉通过打款-订单 123】")

    matched = DouyinDongzhangStrategy._match_compensation(
        beizhu,
        {"赔付": ["仲裁申诉通过打款"]},
    )

    assert matched == "赔付"
