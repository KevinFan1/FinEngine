from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_index import OrderIndex


class OrderIndexService:
    LOOKUP_CHUNK_SIZE = 5000

    @staticmethod
    async def upsert_order_times(
        db: AsyncSession,
        *,
        org_id: int,
        shop_id: int | None,
        platform_code: str,
        orders: list[dict[str, object]],
        source_file_id: int,
    ) -> int:
        """Bulk upsert order creation time indexes."""
        rows = OrderIndexService._dedupe_rows(
            org_id=org_id,
            shop_id=shop_id,
            platform_code=platform_code,
            orders=orders,
            source_file_id=source_file_id,
        )
        if not rows:
            return 0

        stmt = insert(OrderIndex).values(rows)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=[OrderIndex.platform_code, OrderIndex.order_no],
            index_where=text("is_deleted = false"),
            set_={
                "org_id": excluded.org_id,
                "shop_id": excluded.shop_id,
                "order_created_at": excluded.order_created_at,
                "order_year": excluded.order_year,
                "order_month": excluded.order_month,
                "last_file_id": excluded.last_file_id,
                "extra_data": excluded.extra_data,
                "is_deleted": False,
                "deleted_at": None,
            },
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount or 0

    @staticmethod
    async def get_order_created_times(
        db: AsyncSession,
        *,
        platform_code: str,
        order_nos: list[str],
    ) -> dict[str, datetime]:
        """Load order creation times by platform + order number."""
        cleaned_order_nos = [order_no.strip() for order_no in order_nos if order_no and order_no.strip()]
        if not cleaned_order_nos:
            return {}

        found: dict[str, datetime] = {}
        unique_order_nos = list(dict.fromkeys(cleaned_order_nos))
        for start in range(0, len(unique_order_nos), OrderIndexService.LOOKUP_CHUNK_SIZE):
            chunk = unique_order_nos[start : start + OrderIndexService.LOOKUP_CHUNK_SIZE]
            result = await db.execute(
                select(OrderIndex.order_no, OrderIndex.order_created_at).where(
                    OrderIndex.platform_code == platform_code,
                    OrderIndex.order_no.in_(chunk),
                    OrderIndex.is_deleted.is_(False),
                )
            )
            for order_no, order_created_at in result.all():
                found[order_no] = order_created_at
        return found

    @staticmethod
    def _dedupe_rows(
        *,
        org_id: int,
        shop_id: int | None,
        platform_code: str,
        orders: list[dict[str, object]],
        source_file_id: int,
    ) -> list[dict[str, object]]:
        deduped: dict[str, dict[str, object]] = {}
        for order in orders:
            order_no = str(order.get("order_no") or "").strip()
            order_created_at = order.get("order_created_at")
            if not order_no or not isinstance(order_created_at, datetime):
                continue

            deduped[order_no] = {
                "org_id": org_id,
                "shop_id": shop_id,
                "platform_code": platform_code,
                "order_no": order_no,
                "order_created_at": order_created_at,
                "order_year": order_created_at.year,
                "order_month": order_created_at.month,
                "first_file_id": source_file_id,
                "last_file_id": source_file_id,
                "extra_data": order.get("extra_data"),
                "is_deleted": False,
                "deleted_at": None,
            }
        return list(deduped.values())
