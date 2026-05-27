"""Helpers for hiding business data linked to soft-deleted shops."""

from sqlalchemy import exists, select

from app.models.shop import Shop


def active_shop_filter(shop_id_column):
    """Return a SQLAlchemy condition that keeps unscoped rows and active shops only."""
    return shop_id_column.is_(None) | exists(
        select(1).select_from(Shop).where(
            Shop.id == shop_id_column,
            Shop.is_deleted.is_(False),
        )
    )
