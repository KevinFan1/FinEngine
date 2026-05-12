from __future__ import annotations

from hashlib import sha1


SHOP_COLOR_PALETTE = [
    "#F59E0B",
    "#38BDF8",
    "#F97316",
    "#14B8A6",
    "#FB7185",
    "#C084FC",
    "#84CC16",
    "#06B6D4",
    "#F43F5E",
    "#A78BFA",
]


def normalize_shop_color(value: str | None) -> str | None:
    if not value:
        return None
    color = value.strip().upper()
    if not color:
        return None
    if not color.startswith("#"):
        color = f"#{color}"
    return color[:7]


def assign_default_shop_color(*, org_id: int, platform_name: str, shop_name: str) -> str:
    seed = f"{org_id}:{platform_name}:{shop_name}".encode("utf-8")
    index = int(sha1(seed).hexdigest(), 16) % len(SHOP_COLOR_PALETTE)
    return SHOP_COLOR_PALETTE[index]
