"""Seed global transaction-accounting subjects, categories, and rules.

Usage:
    cd backend && python -m scripts.seed_transaction_accounting_defaults
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.services.transaction_accounting_seed_service import DEFAULT_TRANSACTION_RULE_ROWS, TransactionAccountingSeedService


async def seed():
    async with async_session_factory() as db:
        await TransactionAccountingSeedService.seed_defaults(db)
        await db.commit()
        print(f"[OK] Seed global transaction accounting defaults complete: rules={len(DEFAULT_TRANSACTION_RULE_ROWS)}")


if __name__ == "__main__":
    asyncio.run(seed())
