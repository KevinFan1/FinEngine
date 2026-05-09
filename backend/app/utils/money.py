"""Money helpers used by financial processors and aggregation."""

from decimal import Decimal, InvalidOperation
from typing import Iterable

ZERO_MONEY = Decimal("0")


def safe_decimal(value: object, default: Decimal = ZERO_MONEY) -> Decimal:
    """Convert Excel/API values to Decimal without introducing float noise."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))

    s = str(value).strip()
    if not s or s in {"-", "--", "—"}:
        return default

    negative_by_brackets = (s.startswith("(") and s.endswith(")")) or (s.startswith("（") and s.endswith("）"))
    if negative_by_brackets:
        s = s[1:-1]

    s = (
        s.replace(",", "")
        .replace("，", "")
        .replace("￥", "")
        .replace("¥", "")
        .replace("元", "")
        .replace(" ", "")
    )

    try:
        amount = Decimal(s)
    except (InvalidOperation, ValueError):
        return default

    return -amount if negative_by_brackets else amount


def sum_money(values: Iterable[object]) -> Decimal:
    """Sum a series of values as Decimal money."""
    total = ZERO_MONEY
    for value in values:
        total += safe_decimal(value)
    return total
