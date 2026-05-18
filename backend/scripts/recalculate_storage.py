"""重新计算所有组织的存储使用量。

使用方法:
    uv run python scripts/recalculate_storage.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.organization import Organization
from app.services.quota_service import QuotaService


async def main():
    """重新计算所有组织的存储使用量。"""
    async with async_session_factory() as db:
        # 获取所有组织
        result = await db.execute(
            select(Organization).where(Organization.is_deleted.is_(False))
        )
        orgs = result.scalars().all()

        print(f"找到 {len(orgs)} 个组织，开始重新计算存储使用量...\n")

        for org in orgs:
            total_bytes = await QuotaService.recalculate_storage_usage(db, org.id)
            total_gb = round(total_bytes / (1024 ** 3), 2)
            max_gb = round(org.max_storage_bytes / (1024 ** 3), 2)
            usage_percent = round(total_bytes / org.max_storage_bytes * 100, 2) if org.max_storage_bytes > 0 else 0

            print(f"组织 [{org.name}] (ID: {org.id})")
            print(f"  - 存储使用: {total_gb}GB / {max_gb}GB ({usage_percent}%)")
            print(f"  - 套餐类型: {org.plan_type}")
            print()

        await db.commit()
        print("✅ 所有组织的存储使用量已重新计算完成")


if __name__ == "__main__":
    asyncio.run(main())
