"""Default seed data for global transaction accounting rules."""

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.transaction_accounting_rules import (
    TRANSACTION_ACCOUNTING_PENDING_RULES,
    TRANSACTION_ACCOUNTING_RULE_SPECS,
    TransactionAccountingRuleSpec,
)
from app.models.transaction_accounting import TransactionCategory, TransactionDetail, TransactionRule, TransactionSubject


class TransactionAccountingSeedService:
    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        specs = (*TRANSACTION_ACCOUNTING_RULE_SPECS, *TRANSACTION_ACCOUNTING_PENDING_RULES)
        await TransactionAccountingSeedService._reset_rules(db)
        subjects: dict[str, TransactionSubject] = {}
        categories: dict[tuple[str, str], TransactionCategory] = {}
        subject_sort = 10
        category_sort_by_subject: dict[str, int] = {}

        for index, rule_spec in enumerate(specs, start=1):
            subject = subjects.get(rule_spec.subject)
            if subject is None:
                subject = await TransactionAccountingSeedService._get_or_create_subject(
                    db,
                    name=rule_spec.subject,
                    sort_order=subject_sort,
                )
                subjects[rule_spec.subject] = subject
                category_sort_by_subject[rule_spec.subject] = 10
                subject_sort += 10

            category_key = (rule_spec.subject, rule_spec.category)
            category = categories.get(category_key)
            if category is None:
                category = await TransactionAccountingSeedService._get_or_create_category(
                    db,
                    subject_id=subject.id,
                    name=rule_spec.category,
                    sort_order=category_sort_by_subject[rule_spec.subject],
                )
                categories[category_key] = category
                category_sort_by_subject[rule_spec.subject] += 10

            if not rule_spec.enabled:
                continue

            await TransactionAccountingSeedService._get_or_create_rule(
                db,
                subject_id=subject.id,
                category_id=category.id,
                rule_spec=rule_spec,
                priority=index * 10,
            )

    @staticmethod
    async def _reset_rules(db: AsyncSession) -> None:
        await db.execute(update(TransactionDetail).where(TransactionDetail.rule_id.is_not(None)).values(rule_id=None))
        await db.execute(delete(TransactionRule))

    @staticmethod
    async def _get_or_create_subject(db: AsyncSession, *, name: str, sort_order: int) -> TransactionSubject:
        result = await db.execute(
            select(TransactionSubject).where(
                TransactionSubject.name == name,
                TransactionSubject.account_type == "动账账户",
                TransactionSubject.is_deleted.is_(False),
            )
        )
        subject = result.scalar_one_or_none()
        if subject is not None:
            return subject
        subject = TransactionSubject(name=name, account_type="动账账户", sort_order=sort_order, status=1)
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
        rule_spec: TransactionAccountingRuleSpec,
        priority: int,
    ) -> TransactionRule:
        result = await db.execute(
            select(TransactionRule).where(
                TransactionRule.subject_id == subject_id,
                TransactionRule.category_id == category_id,
                TransactionRule.platform_code == "douyin",
                TransactionRule.transaction_direction == rule_spec.transaction_direction,
                TransactionRule.transaction_scene == rule_spec.transaction_scene,
                TransactionRule.match_type == rule_spec.match_type,
                TransactionRule.remark_pattern == rule_spec.remark_pattern,
                TransactionRule.remark_exclude_pattern == rule_spec.remark_exclude_pattern,
                TransactionRule.amount_field == rule_spec.amount_field,
                TransactionRule.result_direction == rule_spec.result_direction,
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
            transaction_direction=rule_spec.transaction_direction,
            transaction_scene=rule_spec.transaction_scene,
            remark_field="备注",
            direction_field="动账方向",
            match_type=rule_spec.match_type,
            remark_pattern=rule_spec.remark_pattern,
            remark_exclude_pattern=rule_spec.remark_exclude_pattern,
            amount_field=rule_spec.amount_field,
            result_direction=rule_spec.result_direction,
            priority=priority,
            status=1,
        )
        db.add(rule)
        await db.flush()
        return rule
