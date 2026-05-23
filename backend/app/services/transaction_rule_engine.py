"""Rule engine for the independent transaction-accounting flow."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.tasks.processors.base import safe_str

ZERO = Decimal("0")


@dataclass(frozen=True)
class TransactionRuleCandidate:
    id: int
    subject_id: int
    category_id: int
    transaction_direction: str
    direction_field: str = "动账方向"
    scene_field: str = "动账场景"
    remark_field: str = "备注"
    match_type: str = "none"
    transaction_scene: str | None = None
    remark_pattern: str = ""
    remark_exclude_pattern: str = ""
    amount_field: str = "动账金额"
    result_direction: str = "original"
    priority: int = 100


@dataclass(frozen=True)
class TransactionEvaluationResult:
    row_number: int
    status: str
    rule_id: int | None
    subject_id: int | None
    category_id: int | None
    amount_field: str | None
    original_amount: Decimal
    calculated_amount: Decimal
    error_message: str | None = None


def evaluate_transaction_row(
    *,
    row: dict[str, object],
    row_number: int,
    rules: list[TransactionRuleCandidate],
    direction_field: str,
    scene_field: str = "动账场景",
    remark_field: str = "备注",
) -> TransactionEvaluationResult:
    results = evaluate_transaction_row_matches(
        row=row,
        row_number=row_number,
        rules=rules,
        direction_field=direction_field,
        scene_field=scene_field,
        remark_field=remark_field,
    )
    return results[0]


def evaluate_transaction_row_matches(
    *,
    row: dict[str, object],
    row_number: int,
    rules: list[TransactionRuleCandidate],
    direction_field: str,
    scene_field: str = "动账场景",
    remark_field: str = "备注",
) -> list[TransactionEvaluationResult]:
    direction = safe_str(row.get(direction_field))
    scene = safe_str(row.get(scene_field))
    remark = safe_str(row.get(remark_field))
    matched_rules = _match_rules(direction=direction, scene=scene, remark=remark, rules=rules)
    if not matched_rules:
        return [
            TransactionEvaluationResult(
                row_number=row_number,
                status="unmatched",
                rule_id=None,
                subject_id=None,
                category_id=None,
                amount_field=None,
                original_amount=ZERO,
                calculated_amount=ZERO,
                error_message="未匹配到动账核算规则",
            )
        ]

    results = []
    for matched_rule in matched_rules:
        amount_field, parsed_amount, error_message = _resolve_amount_value(row=row, amount_field=matched_rule.amount_field)
        if parsed_amount is None:
            results.append(
                _failed_result(
                    row_number=row_number,
                    rule=matched_rule,
                    amount_field=amount_field,
                    message=error_message or f"取数字段 [{amount_field}] 金额无法解析",
                )
            )
            continue

        results.append(
            TransactionEvaluationResult(
                row_number=row_number,
                status="matched",
                rule_id=matched_rule.id,
                subject_id=matched_rule.subject_id,
                category_id=matched_rule.category_id,
                amount_field=amount_field,
                original_amount=parsed_amount,
                calculated_amount=_apply_result_direction(
                    amount=parsed_amount,
                    transaction_direction=direction,
                    result_direction=matched_rule.result_direction,
                ),
            )
        )
    return results


def _match_rule(
    *,
    direction: str,
    scene: str,
    remark: str,
    rules: list[TransactionRuleCandidate],
) -> TransactionRuleCandidate | None:
    candidates = _match_rules(direction=direction, scene=scene, remark=remark, rules=rules)
    if not candidates:
        return None
    return candidates[0]


def _match_rules(
    *,
    direction: str,
    scene: str,
    remark: str,
    rules: list[TransactionRuleCandidate],
) -> list[TransactionRuleCandidate]:
    candidates = [
        rule
        for rule in rules
        if safe_str(rule.transaction_direction) == direction
        and _scene_matches(rule=rule, scene=scene)
        and _remark_matches(rule=rule, remark=remark)
    ]
    return sorted(candidates, key=lambda rule: (rule.priority, rule.id))


def _scene_matches(*, rule: TransactionRuleCandidate, scene: str) -> bool:
    if rule.transaction_scene is None:
        return True
    return scene == safe_str(rule.transaction_scene)


def _remark_matches(*, rule: TransactionRuleCandidate, remark: str) -> bool:
    if _remark_excludes(rule=rule, remark=remark):
        return False

    match_type = safe_str(rule.match_type) or "none"
    if match_type == "none":
        return True

    pattern = safe_str(rule.remark_pattern)
    if not pattern:
        return False

    if match_type == "exact":
        return remark == pattern
    if match_type == "contains":
        patterns = _split_remark_patterns(pattern)
        return bool(patterns) and all(item in remark for item in patterns)
    if match_type == "not_contains":
        patterns = _split_remark_patterns(pattern)
        return bool(patterns) and all(item not in remark for item in patterns)
    return False


def _remark_excludes(*, rule: TransactionRuleCandidate, remark: str) -> bool:
    patterns = _split_remark_patterns(rule.remark_exclude_pattern)
    return any(pattern in remark for pattern in patterns)


def _split_remark_patterns(pattern_text: str) -> list[str]:
    text = safe_str(pattern_text)
    if not text:
        return []
    for separator in ("\r\n", "\n", "\r", ",", "，", "、", ";", "；"):
        text = text.replace(separator, "\n")
    return [part.strip() for part in text.split("\n") if part.strip()]


def _parse_amount(value: object) -> Decimal | None:
    text = safe_str(value)
    if not text:
        return None
    normalized = text.replace(",", "").replace("，", "").replace("￥", "").replace("¥", "").replace("元", "").strip()
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _resolve_amount_value(
    *,
    row: dict[str, object],
    amount_field: str,
) -> tuple[str | None, Decimal | None, str | None]:
    fallback_field = "动账金额"
    candidates = [amount_field]
    if amount_field != fallback_field:
        candidates.append(fallback_field)

    for index, field in enumerate(candidates):
        if field not in row:
            continue
        raw_value = row.get(field)
        if safe_str(raw_value) == "":
            continue
        parsed_amount = _parse_amount(raw_value)
        if parsed_amount is not None:
            return field, parsed_amount, None
        return field, None, f"取数字段 [{field}] 金额无法解析"

    if amount_field != fallback_field:
        return fallback_field, None, f"取数字段 [{amount_field}] 不存在，且取数字段 [动账金额] 不存在"
    return amount_field, None, f"取数字段 [{amount_field}] 不存在"


def _apply_result_direction(
    *,
    amount: Decimal,
    transaction_direction: str,
    result_direction: str,
) -> Decimal:
    if result_direction == "positive":
        return abs(amount)
    if result_direction == "negative":
        return -abs(amount)
    if result_direction == "directional":
        return abs(amount) if transaction_direction == "入账" else -abs(amount)
    return amount


def _failed_result(
    *,
    row_number: int,
    rule: TransactionRuleCandidate,
    amount_field: str | None,
    message: str,
) -> TransactionEvaluationResult:
    return TransactionEvaluationResult(
        row_number=row_number,
        status="failed",
        rule_id=rule.id,
        subject_id=rule.subject_id,
        category_id=rule.category_id,
        amount_field=amount_field or rule.amount_field,
        original_amount=ZERO,
        calculated_amount=ZERO,
        error_message=message,
    )
