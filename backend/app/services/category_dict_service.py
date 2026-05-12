"""Category dict service — CRUD + classify helpers."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category_dict import CategoryDict
from app.schemas.category_dict import CategoryDictCreate, CategoryDictUpdate


class CategoryDictService:
    @staticmethod
    async def get_by_platform_and_type(
        db: AsyncSession,
        *,
        platform_id: int,
        type_code: str,
    ) -> CategoryDict | None:
        """获取指定平台+类型的启用字典。"""
        stmt = (
            select(CategoryDict)
            .where(
                CategoryDict.platform_id == platform_id,
                CategoryDict.type_code == type_code,
                CategoryDict.status == 1,
                CategoryDict.is_deleted.is_(False),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_categories(
        db: AsyncSession,
        *,
        platform_id: int,
        type_code: str,
    ) -> dict[str, list[str]] | None:
        """获取分类字典的 categories 字段。"""
        cd = await CategoryDictService.get_by_platform_and_type(
            db,
            platform_id=platform_id,
            type_code=type_code,
        )
        return cd.categories if cd else None

    @staticmethod
    async def list_dicts(
        db: AsyncSession,
        *,
        platform_id: int | None = None,
        type_code: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CategoryDict], int]:
        """分页列出分类字典。"""
        stmt = select(CategoryDict).where(CategoryDict.is_deleted.is_(False)).order_by(CategoryDict.id)
        count_stmt = select(func.count()).select_from(CategoryDict).where(CategoryDict.is_deleted.is_(False))

        if platform_id is not None:
            stmt = stmt.where(CategoryDict.platform_id == platform_id)
            count_stmt = count_stmt.where(CategoryDict.platform_id == platform_id)
        if type_code:
            stmt = stmt.where(CategoryDict.type_code == type_code)
            count_stmt = count_stmt.where(CategoryDict.type_code == type_code)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def create_dict(
        db: AsyncSession,
        *,
        data: CategoryDictCreate,
    ) -> CategoryDict:
        cd = CategoryDict(
            platform_id=data.platform_id,
            type_code=data.type_code,
            name=data.name,
            categories=data.categories,
            status=data.status,
        )
        db.add(cd)
        await db.flush()
        await db.refresh(cd)
        return cd

    @staticmethod
    async def update_dict(
        db: AsyncSession,
        *,
        dict_id: int,
        data: CategoryDictUpdate,
    ) -> CategoryDict | None:
        result = await db.execute(select(CategoryDict).where(CategoryDict.id == dict_id, CategoryDict.is_deleted.is_(False)))
        cd = result.scalar_one_or_none()
        if cd is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cd, field, value)
        await db.flush()
        await db.refresh(cd)
        return cd

    @staticmethod
    async def delete_dict(
        db: AsyncSession,
        *,
        dict_id: int,
    ) -> bool:
        result = await db.execute(select(CategoryDict).where(CategoryDict.id == dict_id, CategoryDict.is_deleted.is_(False)))
        cd = result.scalar_one_or_none()
        if cd is None:
            return False
        cd.is_deleted = True
        cd.deleted_at = datetime.now(timezone.utc)
        cd.status = 0
        await db.flush()
        return True
