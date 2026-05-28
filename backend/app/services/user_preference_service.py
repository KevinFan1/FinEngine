from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference


class UserPreferenceService:
    @staticmethod
    async def get_preference(
        db: AsyncSession,
        *,
        user_id: int,
        preference_key: str,
    ) -> UserPreference | None:
        result = await db.execute(
            select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.preference_key == preference_key,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def set_preference(
        db: AsyncSession,
        *,
        user_id: int,
        preference_key: str,
        preference_value: Any,
    ) -> UserPreference:
        stmt = (
            insert(UserPreference)
            .values(
                user_id=user_id,
                preference_key=preference_key,
                preference_value=preference_value,
            )
            .on_conflict_do_update(
                index_elements=[UserPreference.user_id, UserPreference.preference_key],
                set_={"preference_value": preference_value},
            )
            .returning(UserPreference)
        )
        result = await db.execute(stmt)
        return result.scalar_one()
