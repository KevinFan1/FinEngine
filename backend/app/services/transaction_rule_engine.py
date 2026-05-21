"""Rule engine for the independent transaction-accounting flow."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.tasks.processors.base import canonical_remark, safe_str

ZERO = Decimal("0")


@dataclass(frozen=True)
class TransactionRuleCandidate:
    id: int
    subject_id: int
    category_id: int
    transaction_direction: str
    direction_field: str
    remark_field: str
    match_type: str
    remark_pattern: str
    amount_field: str
    result_direction: str
    priority: int


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
    remark_field: str,
) -> TransactionEvaluationResult:
    results = evaluate_transaction_row_matches(
        row=row,
        row_number=row_number,
        rules=rules,
        direction_field=direction_field,
        remark_field=remark_field,
    )
    return results[0]


def evaluate_transaction_row_matches(
    *,
    row: dict[str, object],
    row_number: int,
    rules: list[TransactionRuleCandidate],
    direction_field: str,
    remark_field: str,
) -> list[TransactionEvaluationResult]:
    direction = safe_str(row.get(direction_field))
    remark = canonical_remark(safe_str(row.get(remark_field)))
    print(remark)
    matched_rules = _match_rules(direction=direction, remark=remark, rules=rules)
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
        if matched_rule.amount_field not in row:
            results.append(
                _failed_result(
                    row_number=row_number,
                    rule=matched_rule,
                    message=f"取数字段 [{matched_rule.amount_field}] 不存在",
                )
            )
            continue

        parsed_amount = _parse_amount(row.get(matched_rule.amount_field))
        if parsed_amount is None:
            results.append(
                _failed_result(
                    row_number=row_number,
                    rule=matched_rule,
                    message=f"取数字段 [{matched_rule.amount_field}] 金额无法解析",
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
                amount_field=matched_rule.amount_field,
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
    remark: str,
    rules: list[TransactionRuleCandidate],
) -> TransactionRuleCandidate | None:
    candidates = _match_rules(direction=direction, remark=remark, rules=rules)
    if not candidates:
        return None
    return candidates[0]


def _match_rules(
    *,
    direction: str,
    remark: str,
    rules: list[TransactionRuleCandidate],
) -> list[TransactionRuleCandidate]:
    candidates = [rule for rule in rules if safe_str(rule.transaction_direction) == direction and _remark_matches(rule=rule, remark=remark)]
    return sorted(candidates, key=lambda rule: (rule.priority, rule.id))


def _remark_matches(*, rule: TransactionRuleCandidate, remark: str) -> bool:
    pattern = canonical_remark(safe_str(rule.remark_pattern))
    if not pattern:
        return False

    match_type = safe_str(rule.match_type) or "contains"
    if match_type == "exact":
        return remark == pattern
    if match_type == "regex":
        try:
            return re.search(pattern, remark) is not None
        except re.error:
            return False
    return pattern in remark


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
    message: str,
) -> TransactionEvaluationResult:
    return TransactionEvaluationResult(
        row_number=row_number,
        status="failed",
        rule_id=rule.id,
        subject_id=rule.subject_id,
        category_id=rule.category_id,
        amount_field=rule.amount_field,
        original_amount=ZERO,
        calculated_amount=ZERO,
        error_message=message,
    )
