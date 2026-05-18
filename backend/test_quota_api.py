#!/usr/bin/env python3
"""测试配额 API"""
import asyncio
from sqlalchemy import select
from app.core.database import get_async_session
from app.models.organization import Organization
from app.services.quota_service import QuotaService


async def test_quota():
    """测试配额服务"""
    async for db in get_async_session():
        # 获取第一个组织
        result = await db.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()

        if not org:
            print("没有找到组织")
            return

        print(f"测试组织: {org.name} (ID: {org.id})")

        # 获取配额信息
        quota_info = await QuotaService.get_quota_info(db, org.id)

        print("\n配额信息:")
        print(f"  套餐类型: {quota_info['plan_type']}")
        print(f"  到期时间: {quota_info['plan_expires_at']}")
        print(f"  是否过期: {quota_info['is_expired']}")
        print(f"\n用户配额:")
        print(f"  当前: {quota_info['users']['current']}")
        print(f"  最大: {quota_info['users']['max']}")
        print(f"  使用率: {quota_info['users']['usage_percent']:.1f}%")
        print(f"  是否超限: {quota_info['users']['is_exceeded']}")
        print(f"\n存储配额:")
        print(f"  当前: {quota_info['storage']['current_gb']:.2f} GB")
        print(f"  最大: {quota_info['storage']['max_gb']} GB")
        print(f"  使用率: {quota_info['storage']['usage_percent']:.1f}%")
        print(f"  是否超限: {quota_info['storage']['is_exceeded']}")

        break


if __name__ == "__main__":
    asyncio.run(test_quota())
