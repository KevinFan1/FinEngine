from decimal import Decimal

from app.utils.money import safe_decimal


def test_safe_decimal_parses_money_values() -> None:
    assert safe_decimal("1,234.56") == Decimal("1234.56")
    assert safe_decimal("'83.16") == Decimal("83.16")
    assert safe_decimal("￥1，234.56元") == Decimal("1234.56")
    assert safe_decimal("(12.30)") == Decimal("-12.30")
    assert safe_decimal("（12.30）") == Decimal("-12.30")
    assert safe_decimal(0.1) == Decimal("0.1")
    assert safe_decimal("-") == Decimal("0")
    assert safe_decimal(None) == Decimal("0")
