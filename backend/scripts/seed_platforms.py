"""Seed all supported platforms.

Usage:
    cd backend && python -m scripts.seed_platforms

Platforms:
    douyin       — 抖音
    kuaishou     — 快手
    xiaohongshu  — 小红书
    weixin_video — 微信小店
    taobao       — 淘宝
    alipay       — 支付宝
    qianniu      — 千牛
    tmall        — 天猫
    miniprogram  — 小程序
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.models.platform import Platform
from sqlalchemy import select

# ── Platform definitions ─────────────────────────────────────────────────────
PLATFORMS = [
    {"code": "douyin", "name": "抖音", "sort_order": 1, "parent_code": "douyin", "processor_code": "douyin", "order_scope_code": "douyin"},
    {"code": "kuaishou", "name": "快手", "sort_order": 2, "parent_code": "kuaishou", "processor_code": "kuaishou", "order_scope_code": "kuaishou"},
    {"code": "xiaohongshu", "name": "小红书", "sort_order": 3, "parent_code": "xiaohongshu", "processor_code": "xiaohongshu", "order_scope_code": "xiaohongshu"},
    {"code": "weixin_video", "name": "微信小店", "sort_order": 4, "parent_code": "weixin_video", "processor_code": "weixin_video", "order_scope_code": "weixin_video"},
    {"code": "taobao", "name": "淘宝", "sort_order": 5, "parent_code": "taobao", "processor_code": "taobao", "order_scope_code": "taobao"},
    {"code": "alipay", "name": "支付宝", "sort_order": 6, "parent_code": "taobao", "processor_code": "alipay", "order_scope_code": "taobao"},
    {"code": "qianniu", "name": "千牛", "sort_order": 7, "parent_code": "taobao", "processor_code": "qianniu", "order_scope_code": "taobao"},
    {"code": "tmall", "name": "天猫", "sort_order": 8, "parent_code": "taobao", "processor_code": "tmall", "order_scope_code": "taobao"},
    {"code": "miniprogram", "name": "小程序", "sort_order": 9, "parent_code": "miniprogram", "processor_code": "miniprogram", "order_scope_code": "miniprogram"},
]


async def seed():
    async with async_session_factory() as db:
        created, updated, skipped = 0, 0, 0

        for p in PLATFORMS:
            stmt = select(Platform).where(Platform.code == p["code"])
            result = await db.execute(stmt)
            platform = result.scalar_one_or_none()

            if platform is None:
                platform = Platform(
                    code=p["code"],
                    name=p["name"],
                    parent_code=p["parent_code"],
                    processor_code=p["processor_code"],
                    order_scope_code=p["order_scope_code"],
                    sort_order=p["sort_order"],
                    status=1,
                )
                db.add(platform)
                await db.flush()
                print(f"[+] Created platform: id={platform.id} code={p['code']} name={p['name']}")
                created += 1
            else:
                # Update name & sort_order if changed
                need_update = (
                    platform.name != p["name"]
                    or platform.parent_code != p["parent_code"]
                    or platform.processor_code != p["processor_code"]
                    or platform.order_scope_code != p["order_scope_code"]
                    or platform.sort_order != p["sort_order"]
                )
                if need_update:
                    platform.name = p["name"]
                    platform.parent_code = p["parent_code"]
                    platform.processor_code = p["processor_code"]
                    platform.order_scope_code = p["order_scope_code"]
                    platform.sort_order = p["sort_order"]
                    await db.flush()
                    print(f"[~] Updated platform: id={platform.id} code={p['code']} name={p['name']}")
                    updated += 1
                else:
                    print(f"[=] Platform unchanged: id={platform.id} code={p['code']} name={p['name']}")
                    skipped += 1

        await db.commit()
        print(f"\n[OK] Seed platforms complete: created={created} updated={updated} unchanged={skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
