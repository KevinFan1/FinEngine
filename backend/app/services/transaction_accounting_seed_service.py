"""Default seed data for global transaction accounting rules."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction_accounting import TransactionCategory, TransactionRule, TransactionSubject
from app.tasks.processors.base import canonical_remark


@dataclass(frozen=True)
class DefaultTransactionRule:
    subject: str
    category: str
    transaction_direction: str
    raw_remark: str
    amount_field: str
    result_direction: str

    @property
    def remark_pattern(self) -> str:
        return canonical_remark(self.raw_remark)


def _rule(
    subject: str,
    category: str,
    transaction_direction: str,
    raw_remark: str,
    amount_field: str,
    result_direction_label: str,
) -> DefaultTransactionRule:
    result_direction_map = {
        "原值": "original",
        "取正": "positive",
        "取负": "negative",
    }
    return DefaultTransactionRule(
        subject=subject,
        category=category,
        transaction_direction=transaction_direction,
        raw_remark=raw_remark,
        amount_field=amount_field,
        result_direction=result_direction_map[result_direction_label],
    )


DEFAULT_TRANSACTION_RULE_ROWS: tuple[DefaultTransactionRule, ...] = (
    _rule("收到抖音分账款", "订单结算", "入账", "订单结算", "订单退款", "取负"),
    _rule("收到抖音分账款", "订单结算", "出账", "已退款", "动账金额", "取负"),
    _rule("收到抖音分账款", "订单结算", "出账", "订单号 6946267909343417830，退款金额 199.00 元", "动账金额", "取负"),
    _rule("收到抖音分账款", "订单结算", "入账", "订单结算", "订单实付应结", "取正"),
    _rule("收到抖音分账款", "订单结算", "入账", "极速退款分账", "订单实付应结", "取正"),
    _rule("收到抖音分账款", "订单结算", "入账", "退款失败分账", "动账金额", "取正"),
    _rule("收到抖音分账款", "订单结算", "入账", "退款失败退票", "动账金额", "取正"),
    _rule("收到其他与经营相关的收入", "平台补贴", "出账", "平台补贴扣回", "动账金额", "取负"),
    _rule(
        "收到其他与经营相关的收入",
        "平台补贴",
        "入账",
        "售后已由平台处理完成，消费者退款费用由平台出资赔付商家，详情至【售后工作台】查看",
        "动账金额",
        "取正",
    ),
    _rule("收到其他与经营相关的收入", "平台补贴", "入账", "订单结算", "实际平台补贴", "取正"),
    _rule("收到其他与经营相关的收入", "平台补贴", "入账", "订单结算", "实际抖音支付补贴", "取正"),
    _rule("收到其他与经营相关的收入", "平台补贴", "入账", "订单结算", "实际抖音月付营销补贴", "取正"),
    _rule("支付达人分账佣金", "佣金", "入账", "服务费返还", "佣金", "取负"),
    _rule("支付达人分账佣金", "佣金", "入账", "服务费返还", "招商服务费", "取负"),
    _rule("支付达人分账佣金", "佣金", "入账", "极速退款分账", "佣金", "取负"),
    _rule("支付达人分账佣金", "佣金", "入账", "极速退款分账", "招商服务费", "取负"),
    _rule("支付达人分账佣金", "佣金", "入账", "订单结算", "佣金", "取正"),
    _rule("支付达人分账佣金", "佣金", "入账", "订单结算", "招商服务费", "取正"),
    _rule("支付达人分账佣金", "佣金", "入账", "订单结算", "站外推广费", "取正"),
    _rule("支付抖音平台服务费", "平台服务费", "入账", "服务费返还", "平台服务费", "取负"),
    _rule("支付抖音平台服务费", "平台服务费", "入账", "订单结算", "平台服务费", "取正"),
    _rule("支付抖音平台运费险", "运费险", "出账", "保费扣除", "动账金额", "取正"),
    _rule("支付抖音提现", "提现", "入账", "提现退票", "动账金额", "取负"),
    _rule("支付抖音提现", "提现", "出账", "提现", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "拦截费", "出账", "拦截费", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "赔付", "出账", "撤销“因订单存在「发货超时」问题，对消费者进行赔付”", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "赔付", "出账", "赔付", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "赔付", "出账", "结算单号7552119275511824679_供应链快递拦截费用货物类赔付", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "退款转赔付", "出账", "退款转赔付", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "月付贴息费用", "出账", "抖音月付联合贴息费用返还-6920784133211651777", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "月付贴息费用", "出账", "月付贴息", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "小额打款", "出账", "售后单ID：147149361567971925，仲裁申诉通过打款", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "小额打款", "出账", "小额打款", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "小额打款", "出账", "商家向消费者小额打款", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "小额打款", "出账", "打款", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "捐赠", "出账", "公益商家佣金捐赠", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "可提现充值千川", "出账", "划扣电商货款充值巨量千川", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "返现", "入账", "下单返现金活动追缴用户后商家退回平台返现金额", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "返现", "入账", "全额免单追缴用户后商家退回平台返现金额", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "返现", "入账", "签到领现金追缴用户后商家退回平台返现金额", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "返现", "出账", "下单返现金活动追缴用户后商家退回平台返现金额", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "返现", "出账", "全额免单追缴用户后商家退回平台返现金额", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "返现", "出账", "签到领现金追缴用户后商家退回平台返现金额", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "评价有礼", "出账", "评价有礼活动资金回退", "动账金额", "取负"),
    _rule("支付其他与经营相关的支出", "评价有礼", "出账", "评价有礼保证金", "动账金额", "取正"),
    _rule("支付其他与经营相关的支出", "评价有礼", "出账", "扣除货款充值评价有礼保证金，详情至【流量-营销工具-工具列表-评价有礼】查看", "动账金额", "取正"),
    _rule("支付线上BIC费用", "BIC", "入账", "BIC服务费退票", "动账金额", "取负"),
    _rule("支付线上BIC费用", "BIC", "出账", "支付BIC服务费", "动账金额", "取正"),
    _rule("支付线上BIC费用", "BIC", "出账", "商家集运物流费", "动账金额", "取正"),
    _rule("支付线上BIC费用", "BIC", "出账", "结算单号73568870277929-6-100-供应链QIC费用", "动账金额", "取正"),
    _rule("支付线上BIC费用", "可提现充值BIC", "出账", "聚合账户充值至QIC账户", "动账金额", "取正"),
)

class TransactionAccountingSeedService:
    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        subjects: dict[str, TransactionSubject] = {}
        categories: dict[tuple[str, str], TransactionCategory] = {}
        subject_sort = 10
        category_sort_by_subject: dict[str, int] = {}

        for index, rule_row in enumerate(DEFAULT_TRANSACTION_RULE_ROWS, start=1):
            subject = subjects.get(rule_row.subject)
            if subject is None:
                subject = await TransactionAccountingSeedService._get_or_create_subject(
                    db,
                    name=rule_row.subject,
                    sort_order=subject_sort,
                )
                subjects[rule_row.subject] = subject
                category_sort_by_subject[rule_row.subject] = 10
                subject_sort += 10

            category_key = (rule_row.subject, rule_row.category)
            category = categories.get(category_key)
            if category is None:
                category = await TransactionAccountingSeedService._get_or_create_category(
                    db,
                    subject_id=subject.id,
                    name=rule_row.category,
                    sort_order=category_sort_by_subject[rule_row.subject],
                )
                categories[category_key] = category
                category_sort_by_subject[rule_row.subject] += 10

            await TransactionAccountingSeedService._get_or_create_rule(
                db,
                subject_id=subject.id,
                category_id=category.id,
                rule_row=rule_row,
                priority=index * 10,
            )

    @staticmethod
    async def _get_or_create_subject(db: AsyncSession, *, name: str, sort_order: int) -> TransactionSubject:
        result = await db.execute(
            select(TransactionSubject).where(
                TransactionSubject.name == name,
                TransactionSubject.is_deleted.is_(False),
            )
        )
        subject = result.scalar_one_or_none()
        if subject is not None:
            return subject
        subject = TransactionSubject(name=name, sort_order=sort_order, status=1)
        db.add(subject)
        await db.flush()
        return subject

    @staticmethod
    async def _get_or_create_category(
        db: AsyncSession,
        *,
        subject_id: int,
        name: str,
        sort_order: int,
    ) -> TransactionCategory:
        result = await db.execute(
            select(TransactionCategory).where(
                TransactionCategory.subject_id == subject_id,
                TransactionCategory.name == name,
                TransactionCategory.is_deleted.is_(False),
            )
        )
        category = result.scalar_one_or_none()
        if category is not None:
            return category
        category = TransactionCategory(subject_id=subject_id, name=name, sort_order=sort_order, status=1)
        db.add(category)
        await db.flush()
        return category

    @staticmethod
    async def _get_or_create_rule(
        db: AsyncSession,
        *,
        subject_id: int,
        category_id: int,
        rule_row: DefaultTransactionRule,
        priority: int,
    ) -> TransactionRule:
        result = await db.execute(
            select(TransactionRule).where(
                TransactionRule.subject_id == subject_id,
                TransactionRule.category_id == category_id,
                TransactionRule.platform_code == "douyin",
                TransactionRule.transaction_direction == rule_row.transaction_direction,
                TransactionRule.remark_pattern == rule_row.remark_pattern,
                TransactionRule.amount_field == rule_row.amount_field,
                TransactionRule.result_direction == rule_row.result_direction,
                TransactionRule.is_deleted.is_(False),
            )
        )
        rule = result.scalar_one_or_none()
        if rule is not None:
            return rule

        rule = TransactionRule(
            subject_id=subject_id,
            category_id=category_id,
            platform_code="douyin",
            transaction_direction=rule_row.transaction_direction,
            remark_field="备注",
            direction_field="动账方向",
            match_type="exact",
            remark_pattern=rule_row.remark_pattern,
            amount_field=rule_row.amount_field,
            result_direction=rule_row.result_direction,
            priority=priority,
            status=1,
        )
        db.add(rule)
        await db.flush()
        return rule
