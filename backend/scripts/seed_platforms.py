"""Seed all supported platforms.

Usage:
    cd backend && python -m scripts.seed_platforms

Platforms:
    douyin       — 抖音
    kuaishou     — 快手
    xiaohongshu  — 小红书
    weixin_video — 微信小店
    tmall        — 天猫
    miniprogram  — 小程序
    taobao       — 淘宝
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
    {"code": "douyin", "name": "抖音", "sort_order": 1},
    {"code": "kuaishou", "name": "快手", "sort_order": 2},
    {"code": "xiaohongshu", "name": "小红书", "sort_order": 3},
    {"code": "weixin_video", "name": "微信小店", "sort_order": 4},
    {"code": "tmall", "name": "天猫", "sort_order": 5},
    {"code": "miniprogram", "name": "小程序", "sort_order": 6},
    {"code": "taobao", "name": "淘宝", "sort_order": 7},
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
                    sort_order=p["sort_order"],
                    status=1,
                )
                db.add(platform)
                await db.flush()
                print(f"[+] Created platform: id={platform.id} code={p['code']} name={p['name']}")
                created += 1
            else:
                # Update name & sort_order if changed
                need_update = platform.name != p["name"] or platform.sort_order != p["sort_order"]
                if need_update:
                    platform.name = p["name"]
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
