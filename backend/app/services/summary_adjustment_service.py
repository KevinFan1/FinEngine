"""Summary adjustment service — manual report-level adjustments."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.summary_adjustment import SummaryAdjustment
from app.models.user import User
from app.schemas.summary_adjustment import (
    SUMMARY_ADJUSTMENT_METRIC_LABELS,
    SummaryAdjustmentCreate,
    SummaryAdjustmentUpdate,
    signed_adjustment_amount,
)
from app.services.audit_service import AuditService


ADJUSTABLE_SUMMARY_METRICS = tuple(SUMMARY_ADJUSTMENT_METRIC_LABELS.keys())


class SummaryAdjustmentService:
    @staticmethod
    async def list_adjustments(
        db: AsyncSession,
        *,
        org_id: int,
        source_year: int,
        source_month: int,
        platform_name: str,
        shop_id: int,
        metric_key: str | None = None,
    ) -> list[SummaryAdjustment]:
        stmt = (
            select(SummaryAdjustment)
            .where(
                SummaryAdjustment.org_id == org_id,
                SummaryAdjustment.source_year == source_year,
                SummaryAdjustment.source_month == source_month,
                SummaryAdjustment.platform_name == platform_name,
                SummaryAdjustment.shop_id == shop_id,
                SummaryAdjustment.is_deleted.is_(False),
            )
            .order_by(SummaryAdjustment.created_at.desc(), SummaryAdjustment.id.desc())
        )
        if metric_key:
            stmt = stmt.where(SummaryAdjustment.metric_key == metric_key)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_adjustment(
        db: AsyncSession,
        *,
        data: SummaryAdjustmentCreate,
        current_user: User,
        request: Request,
    ) -> SummaryAdjustment:
        adjustment = SummaryAdjustment(
            org_id=current_user.org_id or 0,
            source_year=data.source_year,
            source_month=data.source_month,
            platform_name=data.platform_name,
            shop_id=data.shop_id,
            shop_name=data.shop_name,
            metric_key=data.metric_key,
            adjustment_amount=signed_adjustment_amount(data.direction, data.amount),
            remark=data.remark,
            created_by=current_user.id,
        )
        db.add(adjustment)
        await db.flush()
        await SummaryAdjustmentService._write_audit_log(
            db,
            request=request,
            current_user=current_user,
            action="create",
            adjustment=adjustment,
            new_value=SummaryAdjustmentService.to_audit_value(adjustment),
        )
        return adjustment

    @staticmethod
    async def update_adjustment(
        db: AsyncSession,
        *,
        adjustment_id: int,
        data: SummaryAdjustmentUpdate,
        current_user: User,
        request: Request,
    ) -> SummaryAdjustment | None:
        adjustment = await SummaryAdjustmentService.get_adjustment(
            db,
            org_id=current_user.org_id or 0,
            adjustment_id=adjustment_id,
        )
        if adjustment is None:
            return None

        old_value = SummaryAdjustmentService.to_audit_value(adjustment)
        if data.metric_key is not None:
            adjustment.metric_key = data.metric_key
        if data.amount is not None or data.direction is not None:
            old_direction = "increase" if Decimal(str(adjustment.adjustment_amount or 0)) >= 0 else "decrease"
            old_amount = abs(Decimal(str(adjustment.adjustment_amount or 0)))
            direction = data.direction or old_direction
            amount = data.amount if data.amount is not None else old_amount
            adjustment.adjustment_amount = signed_adjustment_amount(direction, amount)
        if "remark" in data.model_fields_set:
            adjustment.remark = data.remark
        adjustment.updated_by = current_user.id

        await db.flush()
        await SummaryAdjustmentService._write_audit_log(
            db,
            request=request,
            current_user=current_user,
            action="update",
            adjustment=adjustment,
            old_value=old_value,
            new_value=SummaryAdjustmentService.to_audit_value(adjustment),
        )
        return adjustment

    @staticmethod
    async def delete_adjustment(
        db: AsyncSession,
        *,
        adjustment_id: int,
        current_user: User,
        request: Request,
    ) -> SummaryAdjustment | None:
        adjustment = await SummaryAdjustmentService.get_adjustment(
            db,
            org_id=current_user.org_id or 0,
            adjustment_id=adjustment_id,
        )
        if adjustment is None:
            return None

        old_value = SummaryAdjustmentService.to_audit_value(adjustment)
        adjustment.is_deleted = True
        adjustment.deleted_at = datetime.now(timezone.utc)
        adjustment.deleted_by = current_user.id
        await db.flush()
        await SummaryAdjustmentService._write_audit_log(
            db,
            request=request,
            current_user=current_user,
            action="delete",
            adjustment=adjustment,
            old_value=old_value,
        )
        return adjustment

    @staticmethod
    async def get_adjustment(
        db: AsyncSession,
        *,
        org_id: int,
        adjustment_id: int,
    ) -> SummaryAdjustment | None:
        result = await db.execute(
            select(SummaryAdjustment).where(
                SummaryAdjustment.id == adjustment_id,
                SummaryAdjustment.org_id == org_id,
                SummaryAdjustment.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_adjustment_sums(
        db: AsyncSession,
        *,
        org_id: int,
        source_year: int | None = None,
        source_month: int | None = None,
        platform_name: str | None = None,
        shop_id: int | None = None,
        shop_name: str | None = None,
    ) -> dict[tuple[int, int, str, int, str], dict[str, Decimal]]:
        filters = [
            SummaryAdjustment.org_id == org_id,
            SummaryAdjustment.is_deleted.is_(False),
            SummaryAdjustment.metric_key.in_(ADJUSTABLE_SUMMARY_METRICS),
        ]
        if source_year is not None:
            filters.append(SummaryAdjustment.source_year == source_year)
        if source_month is not None:
            filters.append(SummaryAdjustment.source_month == source_month)
        if platform_name:
            filters.append(SummaryAdjustment.platform_name == platform_name)
        if shop_id is not None:
            filters.append(SummaryAdjustment.shop_id == shop_id)
        if shop_name:
            filters.append(SummaryAdjustment.shop_name.ilike(f"%{shop_name}%"))

        stmt = (
            select(
                SummaryAdjustment.source_year,
                SummaryAdjustment.source_month,
                SummaryAdjustment.platform_name,
                SummaryAdjustment.shop_id,
                SummaryAdjustment.shop_name,
                SummaryAdjustment.metric_key,
                func.coalesce(func.sum(SummaryAdjustment.adjustment_amount), 0).label("amount"),
            )
            .where(*filters)
            .group_by(
                SummaryAdjustment.source_year,
                SummaryAdjustment.source_month,
                SummaryAdjustment.platform_name,
                SummaryAdjustment.shop_id,
                SummaryAdjustment.shop_name,
                SummaryAdjustment.metric_key,
            )
        )

        result = await db.execute(stmt)
        sums: dict[tuple[int, int, str, int, str], dict[str, Decimal]] = {}
        for row in result.mappings().all():
            key = (
                int(row["source_year"] or 0),
                int(row["source_month"] or 0),
                str(row["platform_name"] or ""),
                int(row["shop_id"] or 0),
                str(row["shop_name"] or ""),
            )
            sums.setdefault(key, {})[str(row["metric_key"])] = Decimal(str(row["amount"] or 0))
        return sums

    @staticmethod
    def to_audit_value(adjustment: SummaryAdjustment) -> dict:
        amount = Decimal(str(adjustment.adjustment_amount or 0))
        return {
            "id": adjustment.id,
            "source_year": adjustment.source_year,
            "source_month": adjustment.source_month,
            "platform_name": adjustment.platform_name,
            "shop_id": adjustment.shop_id,
            "shop_name": adjustment.shop_name,
            "metric_key": adjustment.metric_key,
            "metric_label": SUMMARY_ADJUSTMENT_METRIC_LABELS.get(adjustment.metric_key, adjustment.metric_key),
            "direction": "increase" if amount >= 0 else "decrease",
            "amount": str(abs(amount)),
            "adjustment_amount": str(amount),
            "remark": adjustment.remark,
        }

    @staticmethod
    async def _write_audit_log(
        db: AsyncSession,
        *,
        request: Request,
        current_user: User,
        action: str,
        adjustment: SummaryAdjustment,
        old_value: dict | None = None,
        new_value: dict | None = None,
    ) -> None:
        action_label = {"create": "新增", "update": "修改", "delete": "删除"}.get(action, action)
        metric_label = SUMMARY_ADJUSTMENT_METRIC_LABELS.get(adjustment.metric_key, adjustment.metric_key)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        await AuditService.log(
            db,
            user_id=current_user.id,
            username=current_user.username,
            display_name=current_user.display_name,
            org_id=current_user.org_id,
            module="summary_adjustment",
            action=action,
            description=f"用户 [{current_user.display_name}] {action_label}汇总调整 [{adjustment.shop_name} {adjustment.source_year}-{adjustment.source_month:02d} {metric_label}]",
            target_type="summary_adjustment",
            target_id=adjustment.id,
            target_name=f"{adjustment.shop_name}-{metric_label}",
            ip=ip,
            user_agent=ua,
            method=request.method,
            path=str(request.url.path),
            old_value=old_value,
            new_value=new_value,
        )
