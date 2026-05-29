"""Default seed data for the global cash-flow item dictionary."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_flow import CashFlowItem


@dataclass(frozen=True)
class DefaultCashFlowItem:
    code: str
    name: str
    parent_code: str | None
    level: int
    item_type: str
    flow_section: str
    flow_direction: str | None
    summary_method: str
    sort_order: int


def _group(code: str, name: str, flow_section: str, flow_direction: str, sort_order: int) -> DefaultCashFlowItem:
    return DefaultCashFlowItem(
        code=code,
        name=name,
        parent_code=None,
        level=1,
        item_type="group",
        flow_section=flow_section,
        flow_direction=flow_direction,
        summary_method="sum_children",
        sort_order=sort_order,
    )


def _detail(code: str, name: str, parent_code: str, flow_section: str, flow_direction: str, sort_order: int) -> DefaultCashFlowItem:
    return DefaultCashFlowItem(
        code=code,
        name=name,
        parent_code=parent_code,
        level=2,
        item_type="detail",
        flow_section=flow_section,
        flow_direction=flow_direction,
        summary_method="manual",
        sort_order=sort_order,
    )


def _net(code: str, name: str, flow_section: str, sort_order: int) -> DefaultCashFlowItem:
    return DefaultCashFlowItem(
        code=code,
        name=name,
        parent_code=None,
        level=1,
        item_type="net",
        flow_section=flow_section,
        flow_direction="net",
        summary_method="formula",
        sort_order=sort_order,
    )


def _net_line(code: str, name: str, parent_code: str, flow_section: str, sort_order: int) -> DefaultCashFlowItem:
    return DefaultCashFlowItem(
        code=code,
        name=name,
        parent_code=parent_code,
        level=2,
        item_type="net",
        flow_section=flow_section,
        flow_direction="net",
        summary_method="formula",
        sort_order=sort_order,
    )


def _check(code: str, name: str, parent_code: str, flow_section: str, sort_order: int) -> DefaultCashFlowItem:
    return DefaultCashFlowItem(
        code=code,
        name=name,
        parent_code=parent_code,
        level=3,
        item_type="check",
        flow_section=flow_section,
        flow_direction="check",
        summary_method="formula",
        sort_order=sort_order,
    )


DEFAULT_CASH_FLOW_ITEMS: tuple[DefaultCashFlowItem, ...] = (
    _group("A", "经营性现金流入", "operating", "inflow", 10),
    _detail("A1", "收到抖音提现", "A", "operating", "inflow", 11),
    _detail("A2", "收到代销款返还", "A", "operating", "inflow", 12),
    _detail("A3", "收到品牌方分账返佣", "A", "operating", "inflow", 13),
    _detail("A4", "收到其他与经营相关的收入", "A", "operating", "inflow", 14),
    _detail("A5", "收到抖音分账款", "A", "operating", "inflow", 15),
    _detail("A6", "收到品牌方分账返佣", "A", "operating", "inflow", 16),
    _detail("A7", "收到其他与经营相关的收入", "A", "operating", "inflow", 17),
    _group("B", "经营性现金流出", "operating", "outflow", 20),
    _detail("B1", "支付代销款", "B", "operating", "outflow", 21),
    _detail("B2", "支付包装盒、耗材支出", "B", "operating", "outflow", 22),
    _detail("B3", "支付福袋、赠品支出", "B", "operating", "outflow", 23),
    _detail("B4", "支付办公室租金", "B", "operating", "outflow", 24),
    _detail("B5", "支付办公室水电费", "B", "operating", "outflow", 25),
    _detail("B6", "支付宿舍租金", "B", "operating", "outflow", 26),
    _detail("B7", "支付宿舍租金水电费", "B", "operating", "outflow", 27),
    _detail("B8", "支付工资及提成", "B", "operating", "outflow", 28),
    _detail("B9", "支付社保&公积金", "B", "operating", "outflow", 29),
    _detail("B10", "支付线下物流费用", "B", "operating", "outflow", 30),
    _detail("B11", "支付线下质检费用", "B", "operating", "outflow", 31),
    _detail("B12", "支付达人分账佣金", "B", "operating", "outflow", 32),
    _detail("B13", "支付推广及投流费用", "B", "operating", "outflow", 33),
    _detail("B14", "支付税费", "B", "operating", "outflow", 34),
    _detail("B15", "支付其他与经营相关的支出", "B", "operating", "outflow", 35),
    _detail("B16", "支付抖音提现", "B", "operating", "outflow", 36),
    _detail("B17", "支付线上BIC费用", "B", "operating", "outflow", 37),
    _detail("B18", "支付达人分账佣金", "B", "operating", "outflow", 38),
    _detail("B19", "支付抖音平台服务费", "B", "operating", "outflow", 39),
    _detail("B20", "支付抖音平台运费险", "B", "operating", "outflow", 40),
    _detail("B21", "支付其他与经营相关的支出", "B", "operating", "outflow", 41),
    _net("C", "经营性现金净额", "operating", 50),
    _net_line("C1", "经营性现金净额", "C", "operating", 51),
    _net_line("C2", "经营性现金净额", "C", "operating", 52),
    _group("D", "投资性现金流入", "investing", "inflow", 60),
    _detail("D1", "收到变卖固定资产收入", "D", "investing", "inflow", 61),
    _detail("D2", "收到变卖投资标的的收入", "D", "investing", "inflow", 62),
    _detail("D3", "收到分红款", "D", "investing", "inflow", 63),
    _detail("D4", "收到与投资活动相关的收入", "D", "investing", "inflow", 64),
    _group("E", "投资性现金流出", "investing", "outflow", 70),
    _detail("E1", "支付投资款", "E", "investing", "outflow", 71),
    _detail("E2", "支付固定资产", "E", "investing", "outflow", 72),
    _detail("E3", "支付在建工程", "E", "investing", "outflow", 73),
    _detail("E4", "支付与投资活动相关的支出", "E", "investing", "outflow", 74),
    _net("F", "投资性现金净额", "investing", 80),
    _group("G", "筹资性现金流入", "financing", "inflow", 90),
    _detail("G1", "收到投资人的投资款", "G", "financing", "inflow", 91),
    _detail("G2", "收到银行贷款", "G", "financing", "inflow", 92),
    _detail("G3", "收到银行利息收入", "G", "financing", "inflow", 93),
    _detail("G4", "收到其他与筹资相关的收入", "G", "financing", "inflow", 94),
    _detail("G5", "收到非经营性还款", "G", "financing", "inflow", 95),
    _group("H", "筹资性现金流出", "financing", "outflow", 100),
    _detail("H1", "支付银行手续费", "H", "financing", "outflow", 101),
    _detail("H2", "支付借款利息", "H", "financing", "outflow", 102),
    _detail("H3", "支付股东分红款", "H", "financing", "outflow", 103),
    _detail("H4", "支付少数股东分红款", "H", "financing", "outflow", 104),
    _detail("H5", "支付少数股东分红款-直播间", "H", "financing", "outflow", 105),
    _detail("H6", "支付其他与筹资相关的支出", "H", "financing", "outflow", 106),
    _detail("H7", "支出非经营性借款", "H", "financing", "outflow", 107),
    _net("I", "筹资性现金净额", "financing", 110),
)


class CashFlowSeedService:
    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        by_code: dict[str, CashFlowItem] = {}
        for default_item in DEFAULT_CASH_FLOW_ITEMS:
            parent_id = None
            if default_item.parent_code is not None:
                parent = by_code.get(default_item.parent_code)
                if parent is None:
                    raise ValueError(f"现金流父级项目不存在: {default_item.parent_code}")
                parent_id = parent.id

            item = await CashFlowSeedService._get_or_create_item(db, default_item=default_item, parent_id=parent_id)
            by_code[default_item.code] = item

    @staticmethod
    async def _get_or_create_item(db: AsyncSession, *, default_item: DefaultCashFlowItem, parent_id: int | None) -> CashFlowItem:
        result = await db.execute(
            select(CashFlowItem).where(
                CashFlowItem.code == default_item.code,
                CashFlowItem.is_deleted.is_(False),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            item = CashFlowItem(
                code=default_item.code,
                name=default_item.name,
                parent_id=parent_id,
                level=default_item.level,
                item_type=default_item.item_type,
                flow_section=default_item.flow_section,
                flow_direction=default_item.flow_direction,
                summary_method=default_item.summary_method,
                sort_order=default_item.sort_order,
                status=1,
            )
            db.add(item)
            await db.flush()
            return item

        item.name = default_item.name
        item.parent_id = parent_id
        item.level = default_item.level
        item.item_type = default_item.item_type
        item.flow_section = default_item.flow_section
        item.flow_direction = default_item.flow_direction
        item.summary_method = default_item.summary_method
        item.sort_order = default_item.sort_order
        item.status = 1
        await db.flush()
        return item
