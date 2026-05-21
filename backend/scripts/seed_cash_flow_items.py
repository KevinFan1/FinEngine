"""Seed global cash-flow item dictionary.

Usage:
    cd backend && python -m scripts.seed_cash_flow_items
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.services.cash_flow_seed_service import DEFAULT_CASH_FLOW_ITEMS, CashFlowSeedService


async def seed():
    async with async_session_factory() as db:
        await CashFlowSeedService.seed_defaults(db)
        await db.commit()
        print(f"[OK] Seed global cash flow items complete: items={len(DEFAULT_CASH_FLOW_ITEMS)}")


if __name__ == "__main__":
    asyncio.run(seed())
