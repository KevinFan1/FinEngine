"""Seed transaction-accounting major categories and subjects.

Usage:
    cd backend && uv run seed-transaction-major-subjects
    cd backend && uv run python -m scripts.seed_transaction_major_subjects
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.models.cash_flow import CashFlowItem
from app.models.transaction_accounting import TransactionMajorCategory, TransactionSubject


@dataclass(frozen=True)
class SeedLine:
    code: str
    name: str
    account_type: str | None = None


SEED_LINES: tuple[SeedLine, ...] = (
    SeedLine("A", "经营性现金流入"),
    SeedLine("A1", "收到抖音提现", "银行账户"),
    SeedLine("A2", "收到代销款返还", "银行账户"),
    SeedLine("A3", "收到品牌方分账返佣", "银行账户"),
    SeedLine("A4", "收到其他与经营相关的收入", "银行账户"),
    SeedLine("A5", "收到抖音分账款", "动账账户"),
    SeedLine("A6", "收到品牌方分账返佣", "动账账户"),
    SeedLine("A7", "收到其他与经营相关的收入", "动账账户"),
    SeedLine("B", "经营性现金流出"),
    SeedLine("B1", "收到其他与经营相关的收入", "银行账户"),
    SeedLine("B2", "支付包装盒、耗材支出", "银行账户"),
    SeedLine("B3", "支付福袋、赠品支出", "银行账户"),
    SeedLine("B4", "支付办公室租金", "银行账户"),
    SeedLine("B5", "支付办公室水电费", "银行账户"),
    SeedLine("B6", "支付宿舍租金", "银行账户"),
    SeedLine("B7", "支付宿舍租金水电费", "银行账户"),
    SeedLine("B8", "支付工资及提成", "银行账户"),
    SeedLine("B9", "支付社保&公积金", "银行账户"),
    SeedLine("B10", "支付线下物流费用", "银行账户"),
    SeedLine("B11", "支付线下质检费用", "银行账户"),
    SeedLine("B12", "支付达人分账佣金", "银行账户"),
    SeedLine("B13", "支付推广及投流费用", "银行账户"),
    SeedLine("B14", "支付税费", "银行账户"),
    SeedLine("B15", "支付其他与经营相关的支出", "银行账户"),
    SeedLine("B16", "支付抖音提现", "动账账户"),
    SeedLine("B17", "支付线上BIC费用", "动账账户"),
    SeedLine("B18", "支付达人分账佣金", "动账账户"),
    SeedLine("B19", "支付抖音平台服务费", "动账账户"),
    SeedLine("B20", "支付抖音平台运费险", "动账账户"),
    SeedLine("B21", "支付其他与经营相关的支出", "动账账户"),
    SeedLine("C", "经营性现金净额"),
    SeedLine("C1", "经营性现金净额", "银行账户"),
    SeedLine("C2", "经营性现金净额", "动账账户"),
    SeedLine("D", "投资性现金流入"),
    SeedLine("D1", "收到变卖固定资产收入", "银行账户"),
    SeedLine("D2", "收到变卖投资标的的收入", "银行账户"),
    SeedLine("D3", "收到分红款", "银行账户"),
    SeedLine("D4", "收到与投资活动相关的收入", "银行账户"),
    SeedLine("E", "投资性现金流出"),
    SeedLine("E1", "支付投资款", "银行账户"),
    SeedLine("E2", "支付固定资产", "银行账户"),
    SeedLine("E3", "支付在建工程", "银行账户"),
    SeedLine("E4", "支付与投资活动相关的支出", "银行账户"),
    SeedLine("F", "投资性现金净额"),
    SeedLine("G", "筹资性现金流入"),
    SeedLine("G1", "收到投资人的投资款", "银行账户"),
    SeedLine("G2", "收到银行贷款", "银行账户"),
    SeedLine("G3", "收到银行利息收入", "银行账户"),
    SeedLine("G4", "收到其他与筹资相关的收入", "银行账户"),
    SeedLine("G5", "收到非经营性还款", "银行账户"),
    SeedLine("H", "筹资性现金流出"),
    SeedLine("H1", "支付银行手续费", "银行账户"),
    SeedLine("H2", "支付借款利息", "银行账户"),
    SeedLine("H3", "支付股东分红款", "银行账户"),
    SeedLine("H4", "支付少数股东分红款", "银行账户"),
    SeedLine("H5", "支付少数股东分红款-直播间", "银行账户"),
    SeedLine("H6", "支付其他与筹资相关的支出", "银行账户"),
    SeedLine("H7", "支出非经营性借款", "银行账户"),
    SeedLine("I", "筹资性现金净额"),
)

SECTION_BY_PREFIX = {
    "A": ("operating", "inflow"),
    "B": ("operating", "outflow"),
    "C": ("operating", "net"),
    "D": ("investing", "inflow"),
    "E": ("investing", "outflow"),
    "F": ("investing", "net"),
    "G": ("financing", "inflow"),
    "H": ("financing", "outflow"),
    "I": ("financing", "net"),
}


def _parent_code(code: str) -> str | None:
    return None if len(code) == 1 else code[0]


def _cash_flow_attrs(line: SeedLine, sort_order: int, parent_id: int | None) -> dict:
    prefix = line.code[0]
    flow_section, flow_direction = SECTION_BY_PREFIX[prefix]
    is_group = _parent_code(line.code) is None
    is_net = flow_direction == "net"
    return {
        "code": line.code,
        "name": line.name,
        "parent_id": parent_id,
        "level": 1 if is_group else 2,
        "item_type": "net" if is_net else ("group" if is_group else "detail"),
        "flow_section": flow_section,
        "flow_direction": flow_direction,
        "summary_method": "formula" if is_net else ("sum_children" if is_group else "manual"),
        "sort_order": sort_order,
        "status": 1,
    }


async def _get_or_create_cash_flow_item(db, *, line: SeedLine, sort_order: int, parent_id: int | None) -> tuple[CashFlowItem, bool]:
    result = await db.execute(
        select(CashFlowItem).where(
            CashFlowItem.code == line.code,
            CashFlowItem.is_deleted.is_(False),
        )
    )
    item = result.scalar_one_or_none()
    created = item is None
    if item is None:
        item = CashFlowItem(**_cash_flow_attrs(line, sort_order, parent_id))
        db.add(item)
    else:
        for key, value in _cash_flow_attrs(line, sort_order, parent_id).items():
            setattr(item, key, value)
    await db.flush()
    return item, created


async def _get_or_create_major_category(db, *, line: SeedLine, sort_order: int) -> tuple[TransactionMajorCategory, bool]:
    result = await db.execute(
        select(TransactionMajorCategory).where(
            TransactionMajorCategory.name == line.name,
            TransactionMajorCategory.is_deleted.is_(False),
        )
    )
    item = result.scalar_one_or_none()
    created = item is None
    if item is None:
        item = TransactionMajorCategory(name=line.name, sort_order=sort_order, status=1)
        db.add(item)
    else:
        item.sort_order = sort_order
        item.status = 1
    await db.flush()
    return item, created


async def _find_subject(
    db,
    *,
    line: SeedLine,
    major_category: TransactionMajorCategory,
    cash_flow_item: CashFlowItem,
) -> TransactionSubject | None:
    result = await db.execute(
        select(TransactionSubject).where(
            TransactionSubject.cash_flow_item_id == cash_flow_item.id,
            TransactionSubject.is_deleted.is_(False),
        )
    )
    rows = list(result.scalars().all())
    for item in rows:
        if item.account_type == line.account_type and item.name == line.name:
            return item
    if rows:
        return rows[0]

    result = await db.execute(
        select(TransactionSubject).where(
            TransactionSubject.major_category_id == major_category.id,
            TransactionSubject.account_type == line.account_type,
            TransactionSubject.name == line.name,
            TransactionSubject.is_deleted.is_(False),
        )
    )
    item = result.scalars().first()
    if item is not None:
        return item

    result = await db.execute(
        select(TransactionSubject).where(
            TransactionSubject.account_type == line.account_type,
            TransactionSubject.name == line.name,
            TransactionSubject.major_category_id.is_(None),
            TransactionSubject.cash_flow_item_id.is_(None),
            TransactionSubject.is_deleted.is_(False),
        )
    )
    return result.scalars().first()


async def _get_or_create_subject(
    db,
    *,
    line: SeedLine,
    major_category: TransactionMajorCategory,
    cash_flow_item: CashFlowItem,
    sort_order: int,
) -> tuple[TransactionSubject, bool]:
    subject = await _find_subject(
        db,
        line=line,
        major_category=major_category,
        cash_flow_item=cash_flow_item,
    )
    created = subject is None
    if subject is None:
        subject = TransactionSubject(name=line.name)
        db.add(subject)
    subject.name = line.name
    subject.account_type = line.account_type
    subject.major_category_id = major_category.id
    subject.cash_flow_item_id = cash_flow_item.id
    subject.sort_order = sort_order
    subject.status = 1
    await db.flush()
    return subject, created


async def seed() -> None:
    async with async_session_factory() as db:
        cash_by_code: dict[str, CashFlowItem] = {}
        major_by_code: dict[str, TransactionMajorCategory] = {}
        stats = {
            "cash_created": 0,
            "cash_updated": 0,
            "major_created": 0,
            "major_updated": 0,
            "subject_created": 0,
            "subject_updated": 0,
        }

        for index, line in enumerate(SEED_LINES, start=1):
            parent = cash_by_code.get(_parent_code(line.code) or "")
            cash_item, cash_created = await _get_or_create_cash_flow_item(
                db,
                line=line,
                sort_order=index * 10,
                parent_id=parent.id if parent else None,
            )
            cash_by_code[line.code] = cash_item
            stats["cash_created" if cash_created else "cash_updated"] += 1

            if line.account_type is None:
                major, major_created = await _get_or_create_major_category(
                    db,
                    line=line,
                    sort_order=index * 10,
                )
                major_by_code[line.code] = major
                stats["major_created" if major_created else "major_updated"] += 1
                continue

            parent_code = _parent_code(line.code)
            major = major_by_code.get(parent_code or "")
            if major is None:
                raise ValueError(f"科目 [{line.code}] 缺少大类 [{parent_code}]")

            _subject, subject_created = await _get_or_create_subject(
                db,
                line=line,
                major_category=major,
                cash_flow_item=cash_item,
                sort_order=index * 10,
            )
            stats["subject_created" if subject_created else "subject_updated"] += 1

        await db.commit()
        print(
            "[OK] Seed transaction major categories and subjects complete: "
            f"cash_flow created={stats['cash_created']} updated={stats['cash_updated']}, "
            f"major created={stats['major_created']} updated={stats['major_updated']}, "
            f"subjects created={stats['subject_created']} updated={stats['subject_updated']}"
        )


if __name__ == "__main__":
    asyncio.run(seed())
