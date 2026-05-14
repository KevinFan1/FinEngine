from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.shop import Shop
from app.models.user import User
from app.schemas.shop import ShopCreate, ShopUpdate
from app.services.audit_service import AuditService
from app.services.shop_color_service import assign_default_shop_color, normalize_shop_color
from app.services.platform_profile_service import resolve_platform_profile


SHOP_DUPLICATE_MESSAGE = "该平台下已存在同名店铺，请勿重复创建"


class ShopService:
    @staticmethod
    def active_filter() -> ColumnElement[bool]:
        return Shop.is_deleted.is_(False)

    @staticmethod
    async def list_shops(
        db: AsyncSession,
        *,
        org_id: int | None = None,
        keyword: str | None = None,
        platform_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Shop], int]:
        stmt = select(Shop).where(ShopService.active_filter()).order_by(Shop.id.desc())
        count_stmt = select(func.count()).select_from(Shop).where(ShopService.active_filter())
        if org_id:
            stmt = stmt.where(Shop.org_id == org_id)
            count_stmt = count_stmt.where(Shop.org_id == org_id)
        if platform_name:
            platform_values = [item.strip() for item in platform_name.split(",") if item.strip()]
            report_platform_codes = set()
            for platform_value in platform_values:
                profile = await resolve_platform_profile(db, platform_value)
                report_platform_codes.add(profile.report_platform_code)
            if report_platform_codes:
                stmt = stmt.where(Shop.platform_name.in_(report_platform_codes))
                count_stmt = count_stmt.where(Shop.platform_name.in_(report_platform_codes))
        if keyword:
            like = f"%{keyword}%"
            cond = Shop.shop_name.ilike(like) | Shop.entity_name.ilike(like)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        total = (await db.execute(count_stmt)).scalar() or 0
        items = list((await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all())
        return items, total

    @staticmethod
    async def get_shop(db: AsyncSession, shop_id: int) -> Shop | None:
        return (await db.execute(select(Shop).where(Shop.id == shop_id, ShopService.active_filter()))).scalar_one_or_none()

    @staticmethod
    async def create_shop(db: AsyncSession, *, data: ShopCreate, org_id: int, operator: User, ip: str | None = None, user_agent: str | None = None) -> Shop:
        # Check uniqueness
        existing = await db.execute(
            select(Shop).where(
                Shop.org_id == org_id,
                Shop.platform_name == data.platform_name,
                Shop.shop_name == data.shop_name,
                ShopService.active_filter(),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(SHOP_DUPLICATE_MESSAGE)
        shop = Shop(
            org_id=org_id,
            platform_name=data.platform_name,
            shop_name=data.shop_name,
            shop_color=normalize_shop_color(data.shop_color) or assign_default_shop_color(
                org_id=org_id,
                platform_name=data.platform_name,
                shop_name=data.shop_name,
            ),
            entity_name=data.entity_name,
            remark=data.remark,
        )
        db.add(shop)
        await db.flush()
        await db.refresh(shop)
        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=org_id,
            module="shop",
            action="create",
            description=f"创建店铺 [{data.platform_name}] [{data.shop_name}]",
            target_type="shop",
            target_id=shop.id,
            target_name=data.shop_name,
            ip=ip,
            user_agent=user_agent,
        )
        return shop

    @staticmethod
    async def update_shop(db: AsyncSession, *, shop_id: int, data: ShopUpdate, operator: User, ip: str | None = None, user_agent: str | None = None) -> Shop | None:
        shop = await ShopService.get_shop(db, shop_id)
        if not shop:
            return None
        old = {
            "platform_name": shop.platform_name,
            "shop_name": shop.shop_name,
            "shop_color": shop.shop_color,
            "entity_name": shop.entity_name,
            "remark": shop.remark,
        }
        update_data = data.model_dump(exclude_unset=True)
        if "shop_color" in update_data:
            update_data["shop_color"] = normalize_shop_color(update_data["shop_color"])
        if "platform_name" in update_data or "shop_name" in update_data:
            next_platform_name = update_data.get("platform_name") or shop.platform_name
            next_shop_name = update_data.get("shop_name") or shop.shop_name
            existing = await db.execute(
                select(Shop).where(
                    Shop.org_id == shop.org_id,
                    Shop.platform_name == next_platform_name,
                    Shop.shop_name == next_shop_name,
                    Shop.id != shop.id,
                    ShopService.active_filter(),
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(SHOP_DUPLICATE_MESSAGE)
        if not update_data.get("shop_color") and (
            "platform_name" in update_data or "shop_name" in update_data
        ):
            next_platform_name = update_data.get("platform_name") or shop.platform_name
            next_shop_name = update_data.get("shop_name") or shop.shop_name
            update_data["shop_color"] = assign_default_shop_color(
                org_id=shop.org_id,
                platform_name=next_platform_name,
                shop_name=next_shop_name,
            )
        for k, v in update_data.items():
            setattr(shop, k, v)
        await db.flush()
        await db.refresh(shop)
        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=shop.org_id,
            module="shop",
            action="update",
            description=f"修改店铺 [{shop.shop_name}]",
            target_type="shop",
            target_id=shop.id,
            target_name=shop.shop_name,
            ip=ip,
            user_agent=user_agent,
            old_value=old,
            new_value=update_data,
        )
        return shop

    @staticmethod
    async def delete_shop(db: AsyncSession, *, shop_id: int, operator: User, ip: str | None = None, user_agent: str | None = None) -> bool:
        shop = await ShopService.get_shop(db, shop_id)
        if not shop:
            return False
        from datetime import datetime, timezone

        shop.is_deleted = True
        shop.deleted_at = datetime.now(timezone.utc)
        shop.status = 0
        await db.flush()
        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=shop.org_id,
            module="shop",
            action="delete",
            description=f"删除店铺 [{shop.platform_name}] [{shop.shop_name}]",
            target_type="shop",
            target_id=shop_id,
            target_name=shop.shop_name,
            ip=ip,
            user_agent=user_agent,
        )
        return True

    @staticmethod
    async def get_or_create_shop(db: AsyncSession, *, org_id: int, platform_name: str, shop_name: str) -> Shop:
        """Get existing shop or create new one. Used during upload callback."""
        stmt = select(Shop).where(Shop.org_id == org_id, Shop.platform_name == platform_name, Shop.shop_name == shop_name, ShopService.active_filter())
        result = await db.execute(stmt)
        shop = result.scalar_one_or_none()
        if shop is None:
            shop = Shop(
                org_id=org_id,
                platform_name=platform_name,
                shop_name=shop_name,
                shop_color=assign_default_shop_color(
                    org_id=org_id,
                    platform_name=platform_name,
                    shop_name=shop_name,
                ),
            )
            db.add(shop)
            await db.flush()
        return shop
