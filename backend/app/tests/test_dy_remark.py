from app.utils.text_classifier import classify_batch, classify_text, extract_chinese

# 模拟数据库中的字典
category_dict = {
    "小额打款": ["小额打款", "商家向消费者小额打款商品补偿", "商家向消费者小额打款补差价", "晚发立赔"],
    "商家责任赔付": ["因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付", "商责退运费", "因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付订单售后单运单"],
    "退率严重赔付": ["品退率偏高", "品退率严重异常", "商品品退率偏高扣除商家相应金额进行运费赔付"],
    "差评赔付": ["差评率偏高", "差评率严重异常", "商品差评率偏高扣除商家相应金额进行运费赔付"],
    "月付贴息费用": ["先用后付", "营销费用", "抖音月付联合贴息费用划扣"],
    "罚款": ["违约金罚单扣款", "延迟发货扣违约金"],
    "赔付": ["因订单存在发货超时问题对消费者进行赔付", "晚揽立赔平台追回"],
    "捐赠": ["公益捐款支出中国妇女发展基金会"],
}

# 测试用例
test_cases = [
    ("【因商家责任导致消费者申请售后，扣除商家相应金额进行运费赔付-订单6937332647110776166-售后单146758012803855905-运单YT2519033443762】", "商家责任赔付"),
    ("商品差评率严重异常扣除商家相应金额进行运费赔付", "差评赔付"),
    ("商家向消费者小额打款商品补偿", "小额打款"),
    ("先用后付", "月付贴息费用"),
    ("违约金罚单扣款", "罚款"),
    ("这是无法匹配的文本", None),
]

print("=" * 70)
print("  utils/text_classifier.py 测试")
print("=" * 70)

all_passed = True
for text, expected in test_cases:
    result = classify_text(text, category_dict)
    passed = result.category == expected
    all_passed = all_passed and passed
    icon = "✅" if passed else "❌"
    print(f"{icon} 期望={expected}, 实际={result.category}, 匹配方式={result.match_type}")
    print(f"   原文: {text[:50]}...")
    print(f"   中文: {result.chinese_text[:50]}...")
    print()

# 批量测试
print("--- 批量测试 ---")
texts = [t for t, _ in test_cases]
batch_results = classify_batch(texts, category_dict)
for r in batch_results:
    print(f"  {r.category or '未分类':<12} | {r.match_type:<8} | {r.text[:40]}...")

print(f"\n全部通过: {all_passed}")
print("=" * 70)
