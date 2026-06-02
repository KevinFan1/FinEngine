from app.utils.product_code import extract_product_code


def test_extract_product_code_matches_finance_tool_rules() -> None:
    assert extract_product_code("沉香【佳哥专属】26 G16591-沉香鼓珠手串-11mm") == "G16591"
    assert extract_product_code("手链 t20260001 / can999") == "T20260001,CAN999"
    assert extract_product_code("【玉总珠宝】崖柏斜挎-约7-8mm 多样性发一 CAN1400899") == "CAN1400899"
    assert extract_product_code("【子楚专属】3 ZC00100027 S925银镶嵌和田玉戒指") == "ZC00100027"
    assert extract_product_code("【云上珠宝】小叶紫檀108佛珠多圈圆珠手串H200-6mm") == "H200"
    assert extract_product_code("【云上叙】XP002-18K金淡水珍珠小米珠项链3mm（商城）") == "XP002"
    assert extract_product_code("约33*13mmCAN3110492") == "CAN3110492"
    assert extract_product_code("无编码商品") == ""
    assert extract_product_code(None) == ""


def test_extract_product_code_keeps_plus_groups() -> None:
    assert extract_product_code("足金吊坠 CAN123+CAN456 主推款") == "CAN123+CAN456"
    assert extract_product_code("组合 A1234 + B5678 多样性发一件") == "A1234+B5678"
    assert extract_product_code("组合 A1234＋B5678 多样性发一件") == "A1234+B5678"


def test_extract_product_code_keeps_letter_suffixes() -> None:
    assert extract_product_code("直播间 V89909-F 备用款") == "V89909-F"
    assert extract_product_code("【云上叙】淡水珍珠项链-2.5mm V33535-F（商城）") == "V33535-F"
    assert extract_product_code("【云上叙】S925银淡水珍珠项链-3mm-V61416-M（甄选）") == "V61416-M"
    assert extract_product_code("培育祖母绿【小宝珠宝】T69283-K S925银镶培育彩宝耳钉") == "T69283"


def test_extract_product_code_filters_material_codes_and_size_suffixes() -> None:
    assert extract_product_code("S925银镶青金石耳钉-11.5*2mm") == ""
    assert extract_product_code("18K金镶嵌极光吊坠-15mm") == ""
    assert extract_product_code("老山檀手镯-多样性发一件-7x7mm") == ""
    assert extract_product_code("AU750金项链 PT950铂金戒指 S999足银手链") == ""
    assert extract_product_code("淡水珍珠项链-约4.5mm-V45054-25（东哥）") == "V45054"
    assert extract_product_code("【小宝珠宝】27 T44378-S925银镶青金石耳钉") == "T44378"
    assert extract_product_code("【云上雅岚】流萤丨18K绿松手链-多样性发一件-XYGD3089540-B") == "XYGD3089540"
    assert extract_product_code("【云上雅岚】清浅丨18K蜜蜡耳钩-多样性发一件-XYGD343005-D") == "XYGD343005"


def test_extract_product_code_keeps_order_and_removes_duplicates() -> None:
    assert extract_product_code("V12452-S925银玛瑙吊坠 V12452-15（东哥）") == "V12452"
    assert extract_product_code("V11111-F G22222 V11111-F") == "V11111-F,G22222"
