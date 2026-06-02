"""Product-code extraction helpers."""

from __future__ import annotations

import re
import unicodedata


# 商品编码：字母前缀 + 至少 3 位数字。
# 支持组合货号和 F/M 尾缀，例如：
#   CAN1400766+CAN1400842
#   V33535-F / V61416-M
#   约33*13mmCAN3110492
PRODUCT_CODE_TOKEN_PATTERN = r"[A-Z]{1,16}\d{3,16}(?:-[FM](?![A-Z0-9]))?"
PRODUCT_CODE_GROUP_PATTERN = rf"{PRODUCT_CODE_TOKEN_PATTERN}(?:\s*\+\s*{PRODUCT_CODE_TOKEN_PATTERN})*"
PRODUCT_CODE_PATTERN = re.compile(
    rf"(?<![A-Z0-9])({PRODUCT_CODE_GROUP_PATTERN})(?![A-Z0-9])"
    rf"|(?:MM|CM)({PRODUCT_CODE_GROUP_PATTERN})(?![A-Z0-9])"
)

MATERIAL_CODE_BLACKLIST = {
    "S925",
    "S990",
    "S999",
    "AG925",
    "AG990",
    "AG999",
    "AU750",
    "AU916",
    "AU999",
    "G750",
    "G999",
    "PT900",
    "PT950",
    "PT990",
    "PT999",
    "PD950",
    "PD990",
    "PD999",
    "K9",
    "K10",
    "K14",
    "K18",
    "K22",
    "K24",
}


def _is_missing(value: object) -> bool:
    if value is None:
        return True

    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def normalize_product_name(product_name: object) -> str:
    if _is_missing(product_name):
        return ""

    return unicodedata.normalize("NFKC", str(product_name)).upper()


def is_valid_product_code_token(product_code: str) -> bool:
    base_code = product_code.split("-", 1)[0]
    if base_code in MATERIAL_CODE_BLACKLIST:
        return False

    return sum(char.isdigit() for char in base_code) >= 3


def normalize_product_code_group(product_code_group: str) -> str:
    product_codes = re.sub(r"\s*\+\s*", "+", product_code_group).split("+")
    valid_codes = [code for code in product_codes if is_valid_product_code_token(code)]
    return "+".join(valid_codes)


def extract_product_code(product_name: object) -> str:
    """Extract product codes from a platform product name.

    Multiple independent codes are returned as comma-separated uppercase codes.
    Combined codes keep their ``+`` separator.
    """
    text = normalize_product_name(product_name).strip()
    if not text:
        return ""

    product_codes = []
    seen = set()

    for match in PRODUCT_CODE_PATTERN.finditer(text):
        product_code = normalize_product_code_group(match.group(1) or match.group(2))
        if not product_code or product_code in seen:
            continue

        seen.add(product_code)
        product_codes.append(product_code)

    return ",".join(product_codes)
