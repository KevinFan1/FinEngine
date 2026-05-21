from decimal import Decimal
from datetime import datetime
import json
from pathlib import Path

from openpyxl import Workbook
import pytest

from app.services.transaction_rule_engine import (
    TransactionRuleCandidate,
    evaluate_transaction_row,
)
from app.services.transaction_accounting_service import TransactionAccountingService
from app.services.transaction_accounting_seed_service import DEFAULT_TRANSACTION_RULE_ROWS
from app.models.transaction_accounting import (
    TransactionCategory,
    TransactionSubject,
    TransactionTask,
    TransactionUploadFile,
)
from app.tasks.processors.douyin import DOUYIN_DONGZHANG_HEADERS


def make_rule(
    *,
    rule_id: int,
    priority: int = 100,
    match_type: str = "contains",
    remark_pattern: str = "订单结算",
    transaction_direction: str = "入账",
    amount_field: str = "动账金额",
    result_direction: str = "original",
    subject_id: int = 1,
    category_id: int = 10,
) -> TransactionRuleCandidate:
    return TransactionRuleCandidate(
        id=rule_id,
        subject_id=subject_id,
        category_id=category_id,
        transaction_direction=transaction_direction,
        direction_field="动账方向",
        remark_field="备注",
        match_type=match_type,
        remark_pattern=remark_pattern,
        amount_field=amount_field,
        result_direction=result_direction,
        priority=priority,
    )


def test_evaluate_transaction_row_uses_highest_priority_matching_rule() -> None:
    row = {"动账方向": "入账", "备注": "订单结算完成", "动账金额": "12.30"}
    low = make_rule(rule_id=1, priority=50, subject_id=1, category_id=10)
    high = make_rule(rule_id=2, priority=10, subject_id=2, category_id=20)

    result = evaluate_transaction_row(
        row=row,
        row_number=3,
        rules=[low, high],
        direction_field="动账方向",
        remark_field="备注",
    )

    assert result.status == "matched"
    assert result.rule_id == 2
    assert result.subject_id == 2
    assert result.category_id == 20
    assert result.original_amount == Decimal("12.30")
    assert result.calculated_amount == Decimal("12.30")


def test_evaluate_transaction_row_supports_exact_contains_and_regex() -> None:
    exact_row = {"方向": "出账", "备注": "已退款", "金额": "20"}
    contains_row = {"方向": "出账", "备注": "平台补贴扣回", "金额": "30"}
    regex_row = {"方向": "出账", "备注": "订单号 123 退款金额 199.00 元", "金额": "40"}
    rules = [
        make_rule(rule_id=1, match_type="exact", remark_pattern="已退款", transaction_direction="出账", amount_field="金额"),
        make_rule(rule_id=2, match_type="contains", remark_pattern="补贴扣回", transaction_direction="出账", amount_field="金额"),
        make_rule(rule_id=3, match_type="regex", remark_pattern=r"退款金额\s+\d+", transaction_direction="出账", amount_field="金额"),
    ]

    assert evaluate_transaction_row(row=exact_row, row_number=1, rules=rules, direction_field="方向", remark_field="备注").rule_id == 1
    assert evaluate_transaction_row(row=contains_row, row_number=2, rules=rules, direction_field="方向", remark_field="备注").rule_id == 2
    assert evaluate_transaction_row(row=regex_row, row_number=3, rules=rules, direction_field="方向", remark_field="备注").rule_id == 3


def test_evaluate_transaction_row_matches_against_canonical_chinese_remark() -> None:
    row = {
        "动账方向": "出账",
        "备注": "订单号 6946267909343417830，退款金额 199.00 元",
        "动账金额": "199",
    }
    rule = make_rule(
        rule_id=8,
        transaction_direction="出账",
        match_type="exact",
        remark_pattern="订单号退款金额元",
    )

    result = evaluate_transaction_row(
        row=row,
        row_number=2,
        rules=[rule],
        direction_field="动账方向",
        remark_field="备注",
    )

    assert result.status == "matched"
    assert result.rule_id == 8


def test_evaluate_transaction_row_returns_unmatched_without_summary_amount() -> None:
    result = evaluate_transaction_row(
        row={"动账方向": "入账", "备注": "无法识别", "动账金额": "99"},
        row_number=5,
        rules=[make_rule(rule_id=1)],
        direction_field="动账方向",
        remark_field="备注",
    )

    assert result.status == "unmatched"
    assert result.rule_id is None
    assert result.calculated_amount == Decimal("0")
    assert result.error_message == "未匹配到动账核算规则"


def test_evaluate_transaction_row_marks_missing_or_invalid_amount_failed() -> None:
    missing_result = evaluate_transaction_row(
        row={"动账方向": "入账", "备注": "订单结算"},
        row_number=5,
        rules=[make_rule(rule_id=1)],
        direction_field="动账方向",
        remark_field="备注",
    )
    invalid_result = evaluate_transaction_row(
        row={"动账方向": "入账", "备注": "订单结算", "动账金额": "abc"},
        row_number=6,
        rules=[make_rule(rule_id=1)],
        direction_field="动账方向",
        remark_field="备注",
    )

    assert missing_result.status == "failed"
    assert missing_result.error_message == "取数字段 [动账金额] 不存在"
    assert invalid_result.status == "failed"
    assert invalid_result.error_message == "取数字段 [动账金额] 金额无法解析"


def test_evaluate_transaction_row_applies_result_direction() -> None:
    base = {"动账方向": "出账", "备注": "订单结算", "动账金额": "-12.30"}

    assert evaluate_transaction_row(
        row=base,
        row_number=1,
        rules=[make_rule(rule_id=1, transaction_direction="出账", result_direction="positive")],
        direction_field="动账方向",
        remark_field="备注",
    ).calculated_amount == Decimal("12.30")
    assert evaluate_transaction_row(
        row=base,
        row_number=1,
        rules=[make_rule(rule_id=1, transaction_direction="出账", result_direction="negative")],
        direction_field="动账方向",
        remark_field="备注",
    ).calculated_amount == Decimal("-12.30")
    assert evaluate_transaction_row(
        row=base,
        row_number=1,
        rules=[make_rule(rule_id=1, transaction_direction="出账", result_direction="directional")],
        direction_field="动账方向",
        remark_field="备注",
    ).calculated_amount == Decimal("-12.30")


def test_load_douyin_dongzhang_rows_finds_header_after_preface(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "douyin.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["说明", "这不是表头"])
    ws.append(DOUYIN_DONGZHANG_HEADERS)
    row = {header: "" for header in DOUYIN_DONGZHANG_HEADERS}
    row.update(
        {
            "动账时间": "2026-05-01",
            "动帐流水号": "流水1",
            "动账方向": "入账",
            "动账金额": "10.00",
            "下单时间": "2026-05-01",
            "订单实付应结": "10.00",
            "订单退款": "0",
            "平台服务费": "1",
            "佣金": "2",
            "招商服务费": "3",
            "站外推广费": "4",
            "备注": "订单结算",
        }
    )
    ws.append([row[header] for header in DOUYIN_DONGZHANG_HEADERS])
    wb.save(file_path)

    class FakeOss:
        @staticmethod
        def download_to_temp(_oss_key: str, target_path: str) -> None:
            Path(target_path).write_bytes(file_path.read_bytes())

    monkeypatch.setattr("app.services.transaction_accounting_service.oss_service", FakeOss())

    upload_file = TransactionUploadFile(
        id=1,
        org_id=1,
        user_id=1,
        original_name="douyin.xlsx",
        oss_key="x",
        platform_code="douyin",
    )

    headers, rows = TransactionAccountingService._load_douyin_dongzhang_rows_from_oss(upload_file)

    assert "动账方向" in headers
    assert rows[0]["备注"] == "订单结算"
    assert rows[0]["平台服务费"] == "1"
    assert rows[0]["佣金"] == "2"


def test_parse_transaction_filename_uses_existing_upload_naming_rule() -> None:
    parsed = TransactionAccountingService.parse_transaction_filename("26年02月_动账_抖音旗舰店.xlsx")

    assert parsed == {"year": 2026, "month": 2, "shop": "抖音旗舰店"}


def test_default_transaction_accounting_seed_rules_are_structured_from_spec() -> None:
    subject_names = list(dict.fromkeys(rule.subject for rule in DEFAULT_TRANSACTION_RULE_ROWS))
    category_keys = list(dict.fromkeys((rule.subject, rule.category) for rule in DEFAULT_TRANSACTION_RULE_ROWS))

    assert len(DEFAULT_TRANSACTION_RULE_ROWS) == 51
    assert len(subject_names) == 8
    assert len(category_keys) == 17
    assert all(rule.remark_pattern for rule in DEFAULT_TRANSACTION_RULE_ROWS)
    assert {rule.result_direction for rule in DEFAULT_TRANSACTION_RULE_ROWS} == {"positive", "negative"}


def test_default_transaction_accounting_seed_rules_store_canonical_remark_patterns() -> None:
    refund_rule = next(rule for rule in DEFAULT_TRANSACTION_RULE_ROWS if rule.raw_remark.startswith("订单号 6946267909343417830"))
    compensation_rule = next(rule for rule in DEFAULT_TRANSACTION_RULE_ROWS if rule.raw_remark.startswith("撤销"))
    bic_rule = next(rule for rule in DEFAULT_TRANSACTION_RULE_ROWS if rule.raw_remark.startswith("结算单号73568870277929"))

    assert refund_rule.remark_pattern == "订单号退款金额元"
    assert compensation_rule.remark_pattern == "撤销因订单存在发货超时问题对消费者进行赔付"
    assert bic_rule.remark_pattern == "结算单号供应链费用"


class _FakeScalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _FakeResult:
    def __init__(self, values: list[object] | None = None) -> None:
        self._values = values or []

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._values)


class _TransactionAccountingSession:
    def __init__(
        self,
        *,
        task: TransactionTask,
        upload_file: TransactionUploadFile,
        subjects: list[TransactionSubject],
        categories: list[TransactionCategory],
        fail_detail_flush: bool = False,
    ) -> None:
        self.task = task
        self.upload_file = upload_file
        self.subjects = subjects
        self.categories = categories
        self.added_rows: list[object] = []
        self.fail_detail_flush = fail_detail_flush
        self.flush_count = 0
        self.rollback_count = 0
        self._transaction_failed = False

    async def get(self, model: type, _item_id: int):
        if model is TransactionTask:
            return self.task
        if model is TransactionUploadFile:
            return self.upload_file
        raise AssertionError(f"unexpected model: {model!r}")

    async def execute(self, stmt):
        statement = str(stmt)
        if "fin_transaction_subjects" in statement:
            return _FakeResult(self.subjects)
        if "fin_transaction_categories" in statement:
            return _FakeResult(self.categories)
        return _FakeResult()

    def add_all(self, rows: list[object]) -> None:
        self.added_rows.extend(rows)

    async def flush(self) -> None:
        self.flush_count += 1
        if self._transaction_failed:
            raise AssertionError("failed task state must be written after rollback")
        if self.fail_detail_flush and self.flush_count == 2:
            self._transaction_failed = True
            raise TypeError("Object of type datetime is not JSON serializable")
        return None

    async def rollback(self) -> None:
        self.rollback_count += 1
        self._transaction_failed = False

    async def refresh(self, _instance: object) -> None:
        return None


@pytest.mark.asyncio
async def test_execute_task_uses_transaction_time_period_and_expands_multi_rule_rows(monkeypatch) -> None:
    task = TransactionTask(id=10, file_id=20, org_id=1, user_id=2, status="queued", progress=0)
    upload_file = TransactionUploadFile(
        id=20,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
    )
    subject_income = TransactionSubject(id=1, name="收到抖音分账款", sort_order=10, status=1)
    subject_subsidy = TransactionSubject(id=2, name="收到其他与经营相关的收入", sort_order=20, status=1)
    category_order = TransactionCategory(id=11, subject_id=1, name="订单结算", sort_order=10, status=1)
    category_subsidy = TransactionCategory(id=21, subject_id=2, name="平台补贴", sort_order=10, status=1)
    db = _TransactionAccountingSession(
        task=task,
        upload_file=upload_file,
        subjects=[subject_income, subject_subsidy],
        categories=[category_order, category_subsidy],
    )
    row = {
        "动账时间": datetime(2026, 3, 15, 10, 0, 0),
        "动账方向": "入账",
        "备注": "订单结算",
        "订单实付应结": "100.00",
        "实际平台补贴": "3.50",
    }
    rules = [
        make_rule(
            rule_id=1,
            priority=10,
            subject_id=1,
            category_id=11,
            transaction_direction="入账",
            remark_pattern="订单结算",
            amount_field="订单实付应结",
            result_direction="positive",
        ),
        make_rule(
            rule_id=2,
            priority=20,
            subject_id=2,
            category_id=21,
            transaction_direction="入账",
            remark_pattern="订单结算",
            amount_field="实际平台补贴",
            result_direction="positive",
        ),
    ]

    async def fake_load_rule_candidates(_db, *, platform_code: str | None) -> list[TransactionRuleCandidate]:
        _ = platform_code
        return rules

    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_douyin_dongzhang_rows_from_oss",
        staticmethod(lambda _upload_file: (["动账时间", "动账方向", "备注", "订单实付应结", "实际平台补贴"], [row])),
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_rule_candidates",
        staticmethod(fake_load_rule_candidates),
    )

    await TransactionAccountingService.execute_task(db, task_id=10)  # type: ignore[arg-type]

    detail_rows = [item for item in db.added_rows if item.__class__.__name__ == "TransactionDetail"]
    summary_rows = [item for item in db.added_rows if item.__class__.__name__ == "TransactionSummaryRow"]

    assert task.status == "success"
    assert task.total_rows == 1
    assert task.matched_rows == 2
    assert task.unmatched_rows == 0
    assert task.failed_rows == 0
    assert len(detail_rows) == 2
    assert {detail.accounting_year for detail in detail_rows} == {2026}
    assert {detail.accounting_month for detail in detail_rows} == {3}
    assert {detail.calculated_amount for detail in detail_rows} == {Decimal("100.00"), Decimal("3.50")}
    assert {detail.raw_row["明细类型"] for detail in detail_rows} == {"聚合明细"}
    assert {detail.raw_row["原始匹配明细数"] for detail in detail_rows} == {1}
    json.dumps(detail_rows[0].raw_row)
    assert task.result_summary == {
        "总行数": 1,
        "匹配明细数": 2,
        "未匹配行数": 0,
        "失败行数": 0,
        "汇总分组数": 2,
    }
    assert len(summary_rows) == 2
    assert {(row.subject_id, row.category_id, row.total_amount) for row in summary_rows} == {
        (1, 11, Decimal("100.00")),
        (2, 21, Decimal("3.50")),
    }


@pytest.mark.asyncio
async def test_execute_task_aggregates_detail_rows_during_processing(monkeypatch) -> None:
    task = TransactionTask(id=11, file_id=21, org_id=1, user_id=2, status="queued", progress=0)
    upload_file = TransactionUploadFile(
        id=21,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
    )
    subject = TransactionSubject(id=1, name="收到抖音分账款", sort_order=10, status=1)
    category = TransactionCategory(id=11, subject_id=1, name="订单结算", sort_order=10, status=1)
    db = _TransactionAccountingSession(
        task=task,
        upload_file=upload_file,
        subjects=[subject],
        categories=[category],
    )
    rows = [
        {
            "动账时间": datetime(2026, 3, 15, 10, 0, 0),
            "动账方向": "入账",
            "备注": "订单结算",
            "订单实付应结": "100.00",
        },
        {
            "动账时间": datetime(2026, 3, 20, 10, 0, 0),
            "动账方向": "入账",
            "备注": "订单结算",
            "订单实付应结": "30.00",
        },
    ]
    rules = [
        make_rule(
            rule_id=1,
            priority=10,
            subject_id=1,
            category_id=11,
            transaction_direction="入账",
            remark_pattern="订单结算",
            amount_field="订单实付应结",
            result_direction="positive",
        )
    ]

    async def fake_load_rule_candidates(_db, *, platform_code: str | None) -> list[TransactionRuleCandidate]:
        _ = platform_code
        return rules

    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_douyin_dongzhang_rows_from_oss",
        staticmethod(lambda _upload_file: (["动账时间", "动账方向", "备注", "订单实付应结"], rows)),
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_rule_candidates",
        staticmethod(fake_load_rule_candidates),
    )

    await TransactionAccountingService.execute_task(db, task_id=11)  # type: ignore[arg-type]

    detail_rows = [item for item in db.added_rows if item.__class__.__name__ == "TransactionDetail"]
    summary_rows = [item for item in db.added_rows if item.__class__.__name__ == "TransactionSummaryRow"]

    assert len(detail_rows) == 1
    assert detail_rows[0].calculated_amount == Decimal("130.00")
    assert detail_rows[0].raw_row["原始匹配明细数"] == 2
    assert len(summary_rows) == 1
    assert summary_rows[0].total_amount == Decimal("130.00")
    assert task.result_summary["汇总分组数"] == 1


@pytest.mark.asyncio
async def test_execute_task_rolls_back_before_persisting_failed_state_after_flush_error(monkeypatch) -> None:
    task = TransactionTask(id=10, file_id=20, org_id=1, user_id=2, status="queued", progress=0)
    upload_file = TransactionUploadFile(
        id=20,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
    )
    subject = TransactionSubject(id=1, name="收到抖音分账款", sort_order=10, status=1)
    category = TransactionCategory(id=11, subject_id=1, name="订单结算", sort_order=10, status=1)
    db = _TransactionAccountingSession(
        task=task,
        upload_file=upload_file,
        subjects=[subject],
        categories=[category],
        fail_detail_flush=True,
    )
    row = {
        "动账时间": datetime(2026, 3, 15, 10, 0, 0),
        "动账方向": "入账",
        "备注": "订单结算",
        "订单实付应结": "100.00",
    }
    rules = [
        make_rule(
            rule_id=1,
            priority=10,
            subject_id=1,
            category_id=11,
            transaction_direction="入账",
            remark_pattern="订单结算",
            amount_field="订单实付应结",
            result_direction="positive",
        )
    ]

    async def fake_load_rule_candidates(_db, *, platform_code: str | None) -> list[TransactionRuleCandidate]:
        _ = platform_code
        return rules

    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_douyin_dongzhang_rows_from_oss",
        staticmethod(lambda _upload_file: (["动账时间", "动账方向", "备注", "订单实付应结"], [row])),
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_rule_candidates",
        staticmethod(fake_load_rule_candidates),
    )

    result = await TransactionAccountingService.execute_task(db, task_id=10)  # type: ignore[arg-type]

    assert db.rollback_count == 1
    assert result.status == "failed"
    assert task.status == "failed"
    assert upload_file.status == "failed"
    assert "Object of type datetime is not JSON serializable" in (task.error_message or "")
