"""Seed default organization and admin users.

Usage:
    cd backend && python -m scripts.seed_users
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.organization import ORG_TYPE_INTERNAL, Organization
from app.models.user import User
from app.services.cash_flow_seed_service import CashFlowSeedService
from app.services.transaction_accounting_seed_service import TransactionAccountingSeedService
from sqlalchemy import select


async def seed():
    async with async_session_factory() as db:
        # ── 1. Default organization ──────────────────────────────────────
        stmt = select(Organization).where(Organization.code == "default")
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()

        if org is None:
            org = Organization(
                name="默认组织",
                code="default",
                org_type=ORG_TYPE_INTERNAL,
                status=1,
                remark="系统初始化自动创建",
            )
            db.add(org)
            await db.flush()
            print(f"[+] Created organization: id={org.id} name=默认组织")
        else:
            print(f"[=] Organization already exists: id={org.id}")

        # ── 2. Superadmin ────────────────────────────────────────────────
        sa_stmt = select(User).where(User.role == "superadmin")
        sa_result = await db.execute(sa_stmt)
        superadmin = sa_result.scalar_one_or_none()

        if superadmin is None:
            superadmin = User(
                org_id=None,
                username="superadmin",
                phone="00000000000",
                password_hash=hash_password("admin123"),
                display_name="超级管理员",
                email=None,
                role="superadmin",
                status=1,
            )
            db.add(superadmin)
            await db.flush()
            print(f"[+] Created superadmin: id={superadmin.id} username=superadmin password=admin123")
        else:
            print(f"[=] Superadmin already exists: id={superadmin.id}")

        # ── 3. Org admin ─────────────────────────────────────────────────
        oa_stmt = select(User).where(User.username == "admin")
        oa_result = await db.execute(oa_stmt)
        org_admin = oa_result.scalar_one_or_none()

        if org_admin is None:
            org_admin = User(
                org_id=org.id,
                username="admin",
                phone="13800000000",
                password_hash=hash_password("admin123"),
                display_name="管理员",
                email=None,
                role="org_admin",
                status=1,
            )
            db.add(org_admin)
            await db.flush()
            print(f"[+] Created org_admin: id={org_admin.id} username=admin password=admin123")
        else:
            print(f"[=] Org admin already exists: id={org_admin.id}")

        await TransactionAccountingSeedService.seed_defaults(db)
        await CashFlowSeedService.seed_defaults(db)

        await db.commit()
        print("[OK] Seed users complete.")


if __name__ == "__main__":
    asyncio.run(seed())
