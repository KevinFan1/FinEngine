"""Default configuration dictionary for transaction accounting rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionAccountingRuleSpec:
    subject: str
    category: str
    transaction_direction: str
    transaction_scene: str | None
    match_type: str = "none"
    remark_pattern: str = ""
    remark_exclude_pattern: str = ""
    amount_field: str = "动账金额"
    result_direction: str = "original"
    priority: int = 100
    enabled: bool = True
    source_rows: tuple[int, ...] = ()
    note: str | None = None


RuleEntry = dict[str, object]
RuleConfig = dict[str, dict[str, list[RuleEntry]]]


TRANSACTION_ACCOUNTING_RULE_CONFIG: RuleConfig = {
    "收到抖音分账款": {
        "订单结算": [
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "订单实付应结",
                "result_direction": "positive",
                "source_rows": (2,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "订单退款",
                "result_direction": "negative",
                "source_rows": (3,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "退款-结算后退款-退用户",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (4,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "退款-极速退二阶段商家资金回补",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (5,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "match_type": "exact",
                "remark_pattern": "极速退款分账",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (6,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "match_type": "exact",
                "remark_pattern": "退款失败分账",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (7,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-结算后退款-退用户",
                "match_type": "exact",
                "remark_pattern": "退款失败退票",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (8,),
            },
        ],
    },
    "收到其他与经营相关的收入": {
        "平台补贴": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "退款-订单退款触发-退补贴",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (9,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "平台赔付",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (10,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "实际平台补贴",
                "result_direction": "positive",
                "source_rows": (11,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "实际抖音支付补贴",
                "result_direction": "positive",
                "source_rows": (12,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "实际抖音月付营销补贴",
                "result_direction": "positive",
                "source_rows": (13,),
            },
        ],
    },
    "支付达人分账佣金": {
        "佣金": [
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-退分账",
                "amount_field": "佣金",
                "result_direction": "negative",
                "source_rows": (14,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-退分账",
                "amount_field": "招商服务费",
                "result_direction": "negative",
                "source_rows": (15,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "amount_field": "佣金",
                "result_direction": "negative",
                "source_rows": (14,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "amount_field": "招商服务费",
                "result_direction": "negative",
                "source_rows": (15,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "match_type": "exact",
                "remark_pattern": "极速退款分账",
                "amount_field": "佣金",
                "result_direction": "negative",
                "source_rows": (16,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "match_type": "exact",
                "remark_pattern": "极速退款分账",
                "amount_field": "招商服务费",
                "result_direction": "negative",
                "source_rows": (17,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "佣金",
                "result_direction": "positive",
                "source_rows": (18,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "招商服务费",
                "result_direction": "positive",
                "source_rows": (19,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "站外推广费",
                "result_direction": "positive",
                "source_rows": (20,),
            },
        ],
    },
    "支付抖音平台服务费": {
        "平台服务费": [
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-退分账",
                "amount_field": "平台服务费",
                "result_direction": "negative",
                "match_type": "exact",
                "remark_pattern": "服务费返还",
                "source_rows": (21,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "amount_field": "平台服务费",
                "result_direction": "negative",
                "match_type": "exact",
                "remark_pattern": "服务费返还",
                "source_rows": (21,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "货款结算入账",
                "amount_field": "平台服务费",
                "result_direction": "positive",
                "source_rows": (22,),
            },
        ],
    },
    "支付抖音平台运费险": {
        "运费险": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "权益保险",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (23,),
            },
        ],
    },
    "支付抖音提现": {
        "提现": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "提现",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (25,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "提现",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (25,),
            },
        ],
    },
    "支付其他与经营相关的支出": {
        "拦截费": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "",
                "match_type": "contains",
                "remark_pattern": "拦截费",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (26,),
            },
        ],
        "赔付": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "消费者赔付",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "match_type": "not_contains",
                "remark_pattern": "打款,订单号",
                "source_rows": (27,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "消费者赔付",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (35,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "上门取件运费",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "match_type": "not_contains",
                "remark_pattern": "打款,订单号",
                "source_rows": (29,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "发货物流违规扣罚",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (29,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "判罚扣款",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (29,),
            },
        ],
        "退款转赔付": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "退款-退转付扣减商家货款",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (32,),
            },
            # {
            #     "transaction_direction": "出账",
            #     "transaction_scene": "小额打款",
            #     "amount_field": "动账金额",
            #     "result_direction": "positive",
            #     "match_type": "contains",
            #     "remark_pattern": "商家向消费者小额打款",
            #     "source_rows": (32,),
            # },
            {
                "transaction_direction": "出账",
                "transaction_scene": "退款-极速退二次售后-退用户",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (32,),
            },
        ],
        "月付贴息费用": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "抖音月付与商家联合贴息活动",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (33,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "抖音月付与商家联合贴息活动",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (34,),
            },
        ],
        "小额打款": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "消费者赔付",
                "amount_field": "动账金额",
                "match_type": "contains",
                "remark_pattern": "打款,订单号",
                "result_direction": "positive",
                "source_rows": (35,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "小额打款",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (36, 37, 38),
            },
        ],
        "捐赠": [
            {
                "transaction_direction": "出账",
                "transaction_scene": None,
                "amount_field": "动账金额",
                "match_type": "contains",
                "remark_pattern": "公益商家佣金捐赠",
                "result_direction": "positive",
                "source_rows": (),
            },
        ],
        "可提现充值千川": [
            {
                "transaction_direction": "出账",
                "transaction_scene": None,
                "amount_field": "动账金额",
                "match_type": "exact",
                "remark_pattern": "划扣电商货款充值巨量千川",
                "result_direction": "positive",
                "source_rows": (),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": None,
                "amount_field": "动账金额",
                "match_type": "exact",
                "remark_pattern": "电商货款充值巨量千川，未消耗充值款退回货款",
                "result_direction": "negative",
                "source_rows": (),
            },
        ],
        "返现": [
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "match_type": "exact",
                "remark_pattern": "下单返现金活动追缴用户后商家退回平台返现金额",
                "source_rows": (43,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "match_type": "exact",
                "remark_pattern": "全额免单追缴用户后商家退回平台返现金额",
                "source_rows": (43,),
            },
            {
                "transaction_direction": "入账",
                "transaction_scene": "退款-订单退款触发-分账",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "match_type": "exact",
                "remark_pattern": "签到领现金追缴用户后商家退回平台返现金额",
                "source_rows": (43,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "平台返现/返券活动追缴用户退回平台",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "match_type": "exact",
                "remark_pattern": "下单返现金活动追缴用户后商家退回平台返现金额",
                "source_rows": (46,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "平台返现/返券活动追缴用户退回平台",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "match_type": "exact",
                "remark_pattern": "全额免单追缴用户后商家退回平台返现金额",
                "source_rows": (46,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "平台返现/返券活动追缴用户退回平台",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "match_type": "exact",
                "remark_pattern": "签到领现金追缴用户后商家退回平台返现金额",
                "source_rows": (46,),
            },
        ],
        "评价有礼": [
            {
                "transaction_direction": "入账",
                "transaction_scene": "评价有礼活动资金回退",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (48,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "评价有礼保证金扣款",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (48,),
            },
        ],
        "可提现充值保证金": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "充值保证金",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (47,),
            },
        ],
    },
    "支付线上BIC费用": {
        "BIC": [
            {
                "transaction_direction": "入账",
                "transaction_scene": "供应链QIC费用",
                "amount_field": "动账金额",
                "result_direction": "negative",
                "source_rows": (49,),
            },
            {
                "transaction_direction": "出账",
                "transaction_scene": "供应链QIC费用",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (50, 52),
            },
        ],
        "可提现充值BIC": [
            {
                "transaction_direction": "出账",
                "transaction_scene": "",
                "match_type": "exact",
                "remark_pattern": "聚合账户充值至QIC账户",
                "amount_field": "动账金额",
                "result_direction": "positive",
                "source_rows": (53,),
            },
        ],
    },
}


TRANSACTION_ACCOUNTING_PENDING_RULE_CONFIG: RuleConfig = {}


def _build_rule_specs(config: RuleConfig, *, enabled: bool) -> tuple[TransactionAccountingRuleSpec, ...]:
    specs: list[TransactionAccountingRuleSpec] = []
    priority = 10
    for subject, categories in config.items():
        for category, rule_entries in categories.items():
            for rule in rule_entries:
                source_rows = tuple(int(row) for row in rule.get("source_rows", ()))
                specs.append(
                    TransactionAccountingRuleSpec(
                        subject=subject,
                        category=category,
                        transaction_direction=str(rule["transaction_direction"]),
                        transaction_scene=_optional_scene(rule.get("transaction_scene")),
                        match_type=str(rule.get("match_type") or "none"),
                        remark_pattern=str(rule.get("remark_pattern") or ""),
                        remark_exclude_pattern=str(rule.get("remark_exclude_pattern") or "").strip(),
                        amount_field=str(rule.get("amount_field") or "动账金额"),
                        result_direction=str(rule.get("result_direction") or "original"),
                        priority=int(rule.get("priority") or priority),
                        enabled=enabled,
                        source_rows=source_rows,
                        note=str(rule.get("note") or _source_note(source_rows)),
                    )
                )
                priority += 10
    return tuple(specs)


def _optional_scene(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _source_note(source_rows: tuple[int, ...]) -> str:
    if not source_rows:
        return "整理.xlsx"
    rows = "、".join(str(row) for row in source_rows)
    return f"整理.xlsx 第{rows}行"


TRANSACTION_ACCOUNTING_RULE_SPECS = _build_rule_specs(
    TRANSACTION_ACCOUNTING_RULE_CONFIG,
    enabled=True,
)
TRANSACTION_ACCOUNTING_PENDING_RULES = _build_rule_specs(
    TRANSACTION_ACCOUNTING_PENDING_RULE_CONFIG,
    enabled=False,
)
