from decimal import Decimal
from datetime import datetime
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from openpyxl import Workbook
import pytest

from app.services.transaction_rule_engine import (
    TransactionRuleCandidate,
    evaluate_transaction_row,
)
from app.services.oss_service import OSSObjectUnavailableError, SOURCE_FILE_UNAVAILABLE_MESSAGE
from app.services.transaction_accounting_service import TransactionAccountingService
from app.config.transaction_accounting_rules import (
    TRANSACTION_ACCOUNTING_PENDING_RULES,
    TRANSACTION_ACCOUNTING_RULE_SPECS,
)
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
    transaction_scene: str | None = None,
    transaction_direction: str = "入账",
    amount_field: str = "动账金额",
    result_direction: str = "original",
    remark_exclude_pattern: str = "",
    subject_id: int = 1,
    category_id: int = 10,
) -> TransactionRuleCandidate:
    return TransactionRuleCandidate(
        id=rule_id,
        subject_id=subject_id,
        category_id=category_id,
        transaction_direction=transaction_direction,
        direction_field="动账方向",
        scene_field="动账场景",
        remark_field="备注",
        match_type=match_type,
        transaction_scene=transaction_scene,
        remark_pattern=remark_pattern,
        remark_exclude_pattern=remark_exclude_pattern,
        amount_field=amount_field,
        result_direction=result_direction,
        priority=priority,
    )


class _FakeDongzhangRowStream:
    def __init__(
        self,
        *,
        header: list[str],
        rows: list[dict[str, object]],
        period: tuple[int, int] = (2026, 2),
    ) -> None:
        self.header = header
        self.header_row_number = 1
        self.rows = ((index, row) for index, row in enumerate(rows, start=2))
        self.period_header = "动账时间"
        self.download_seconds = 0.0
        self.open_seconds = 0.0
        self._period = period

    def resolve_upload_period(self) -> tuple[int, int]:
        return self._period


class _FakeDongzhangRowStreamContext:
    def __init__(self, row_stream: _FakeDongzhangRowStream | Exception) -> None:
        self._row_stream = row_stream

    def __enter__(self) -> _FakeDongzhangRowStream:
        if isinstance(self._row_stream, Exception):
            raise self._row_stream
        return self._row_stream

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        return None


def _mock_dongzhang_row_stream(
    monkeypatch,
    *,
    header: list[str],
    rows: list[dict[str, object]],
    period: tuple[int, int] = (2026, 2),
):
    mock = Mock(
        return_value=_FakeDongzhangRowStreamContext(
            _FakeDongzhangRowStream(header=header, rows=rows, period=period)
        )
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "_iter_douyin_dongzhang_rows_from_oss",
        staticmethod(mock),
    )
    return mock


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


def test_evaluate_transaction_row_supports_exact_contains_and_not_contains() -> None:
    exact_row = {"方向": "出账", "备注": "已退款", "金额": "20"}
    contains_row = {"方向": "出账", "备注": "平台补贴扣回", "金额": "30"}
    not_contains_row = {"方向": "出账", "备注": "仲裁申诉通过打款", "金额": "40"}
    excluded_row = {"方向": "出账", "备注": "打款，订单号 123", "金额": "50"}
    rules = [
        make_rule(rule_id=1, match_type="exact", remark_pattern="已退款", transaction_direction="出账", amount_field="金额"),
        make_rule(rule_id=2, match_type="contains", remark_pattern="平台,扣回", transaction_direction="出账", amount_field="金额"),
        make_rule(rule_id=3, match_type="not_contains", remark_pattern="订单号,流水号", transaction_direction="出账", amount_field="金额"),
    ]

    assert evaluate_transaction_row(row=exact_row, row_number=1, rules=rules, direction_field="方向", remark_field="备注").rule_id == 1
    assert evaluate_transaction_row(row=contains_row, row_number=2, rules=rules, direction_field="方向", remark_field="备注").rule_id == 2
    assert evaluate_transaction_row(row=not_contains_row, row_number=3, rules=rules, direction_field="方向", remark_field="备注").rule_id == 3
    assert evaluate_transaction_row(row=excluded_row, row_number=4, rules=[rules[2]], direction_field="方向", remark_field="备注").status == "unmatched"


def test_evaluate_transaction_row_matches_scene_and_falls_back_to_dongzhang_amount() -> None:
    row = {
        "动账方向": "出账",
        "动账场景": "平台赔付",
        "备注": "仲裁申诉通过打款",
        "动账金额": "88.50",
    }
    rule = make_rule(
        rule_id=4,
        transaction_direction="出账",
        transaction_scene="平台赔付",
        match_type="contains",
        remark_pattern="仲裁申诉通过打款",
        amount_field="实际平台补贴",
    )

    result = evaluate_transaction_row(
        row=row,
        row_number=4,
        rules=[rule],
        direction_field="动账方向",
        remark_field="备注",
    )

    assert result.status == "matched"
    assert result.amount_field == "动账金额"
    assert result.original_amount == Decimal("88.50")
    assert result.calculated_amount == Decimal("88.50")


def test_evaluate_transaction_row_uses_raw_remark_text_without_keyword_canonicalization() -> None:
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

    assert result.status == "unmatched"
    assert result.rule_id is None


def test_evaluate_transaction_row_excludes_remark_contains_patterns() -> None:
    rule = make_rule(
        rule_id=9,
        transaction_direction="出账",
        match_type="contains",
        remark_pattern="打款",
        remark_exclude_pattern="订单号,流水号",
    )

    matched_result = evaluate_transaction_row(
        row={"动账方向": "出账", "备注": "仲裁申诉通过打款", "动账金额": "20"},
        row_number=1,
        rules=[rule],
        direction_field="动账方向",
        remark_field="备注",
    )
    excluded_result = evaluate_transaction_row(
        row={"动账方向": "出账", "备注": "打款，订单号 123", "动账金额": "20"},
        row_number=2,
        rules=[rule],
        direction_field="动账方向",
        remark_field="备注",
    )

    assert matched_result.status == "matched"
    assert matched_result.rule_id == 9
    assert excluded_result.status == "unmatched"
    assert excluded_result.rule_id is None


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
    assert upload_file.accounting_year == 2026
    assert upload_file.accounting_month == 5


def test_parse_transaction_filename_uses_existing_upload_naming_rule() -> None:
    parsed = TransactionAccountingService.parse_transaction_filename("26年02月_动账_抖音旗舰店.xlsx")

    assert parsed == {"year": 2026, "month": 2, "shop": "抖音旗舰店"}


def test_default_transaction_accounting_seed_rules_are_structured_from_spec() -> None:
    all_specs = [*TRANSACTION_ACCOUNTING_RULE_SPECS, *TRANSACTION_ACCOUNTING_PENDING_RULES]
    subject_names = list(dict.fromkeys(rule.subject for rule in all_specs))
    category_keys = list(dict.fromkeys((rule.subject, rule.category) for rule in all_specs))

    assert len(TRANSACTION_ACCOUNTING_RULE_SPECS) == 56
    assert len(TRANSACTION_ACCOUNTING_PENDING_RULES) == 0
    assert len(all_specs) == 56
    assert len(subject_names) == 8
    assert len(category_keys) == 18
    assert all(rule.match_type == "none" or rule.remark_pattern for rule in all_specs)
    assert any(rule.match_type == "not_contains" for rule in TRANSACTION_ACCOUNTING_RULE_SPECS)
    assert {rule.result_direction for rule in TRANSACTION_ACCOUNTING_RULE_SPECS} == {"positive", "negative"}
    if TRANSACTION_ACCOUNTING_PENDING_RULES:
        assert any(rule.enabled is False for rule in TRANSACTION_ACCOUNTING_PENDING_RULES)


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

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None

    def first(self):
        return (self._values[0],) if self._values else None


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


class _ListDetailsResult:
    def __init__(self, *, scalar_value: int = 0, rows: list[object] | None = None) -> None:
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar(self) -> int:
        return self._scalar_value

    def all(self) -> list[object]:
        return self._rows


class _ListDetailsSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, stmt):
        try:
            statement = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        except Exception:
            statement = str(stmt)
        self.statements.append(statement)
        if "count(" in statement:
            return _ListDetailsResult(scalar_value=0)
        return _ListDetailsResult(rows=[])


@pytest.mark.asyncio
async def test_list_details_defaults_to_matched_classified_rows() -> None:
    db = _ListDetailsSession()

    await TransactionAccountingService.list_details(
        db,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),
    )

    statement_text = "\n".join(db.statements)
    assert "fin_transaction_details.status = 'matched'" in statement_text
    assert "fin_transaction_details.subject_id IS NOT NULL" in statement_text
    assert "fin_transaction_details.category_id IS NOT NULL" in statement_text
    assert "fin_transaction_details.shop_id IS NULL" in statement_text
    assert "fin_transaction_upload_files.shop_id IS NULL" in statement_text
    assert "EXISTS" in statement_text
    assert "fin_shops" in statement_text


@pytest.mark.asyncio
async def test_list_tasks_filters_queued_status() -> None:
    db = _ListDetailsSession()

    await TransactionAccountingService.list_tasks(
        db,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),
        status="queued",
    )

    statement_text = "\n".join(db.statements)
    assert "fin_transaction_tasks.status IN ('queued')" in statement_text
    assert "fin_transaction_upload_files.shop_id IS NULL" in statement_text
    assert "EXISTS" in statement_text
    assert "fin_shops" in statement_text


@pytest.mark.asyncio
async def test_list_tasks_supports_multiple_status_filters() -> None:
    db = _ListDetailsSession()

    await TransactionAccountingService.list_tasks(
        db,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),
        status="queued,processing",
    )

    statement_text = "\n".join(db.statements)
    assert "fin_transaction_tasks.status IN ('queued', 'processing')" in statement_text


@pytest.mark.asyncio
async def test_list_tasks_supports_created_time_range_filters() -> None:
    db = _ListDetailsSession()

    await TransactionAccountingService.list_tasks(
        db,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),
        created_start_time=datetime(2026, 5, 1, 8, 0, 0),
        created_end_time=datetime(2026, 5, 2, 18, 30, 0),
    )

    statement_text = "\n".join(db.statements)
    assert "fin_transaction_tasks.created_at >=" in statement_text
    assert "fin_transaction_tasks.created_at <=" in statement_text


@pytest.mark.asyncio
async def test_execute_task_uses_transaction_time_period_and_expands_multi_rule_rows(monkeypatch, caplog) -> None:
    caplog.set_level(logging.INFO, logger="finengine.transaction_accounting")
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

    stream_mock = _mock_dongzhang_row_stream(
        monkeypatch,
        header=["动账时间", "动账方向", "备注", "订单实付应结", "实际平台补贴"],
        rows=[row],
        period=(2026, 2),
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
        "成功行数": 1,
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
    stream_mock.assert_called_once()
    assert sum("transaction_accounting.rule_result" in record.message for record in caplog.records) == 2
    assert sum("transaction_accounting.category_result" in record.message for record in caplog.records) == 2
    assert sum("transaction_accounting.task_perf" in record.message for record in caplog.records) == 1
    assert not any("transaction_accounting.row_multi_rule_match" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_execute_task_marks_header_only_file_success_with_empty_reason(monkeypatch) -> None:
    task = TransactionTask(id=13, file_id=23, org_id=1, user_id=2, status="queued", progress=0)
    upload_file = TransactionUploadFile(
        id=23,
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

    async def fake_load_rule_candidates(_db, *, platform_code: str | None) -> list[TransactionRuleCandidate]:
        _ = platform_code
        return [make_rule(rule_id=1, subject_id=1, category_id=11)]

    _mock_dongzhang_row_stream(
        monkeypatch,
        header=["动账时间", "动账方向", "备注", "订单实付应结"],
        rows=[],
        period=(2026, 2),
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_rule_candidates",
        staticmethod(fake_load_rule_candidates),
    )

    await TransactionAccountingService.execute_task(db, task_id=13)  # type: ignore[arg-type]

    assert task.status == "success"
    assert task.progress == 100
    assert task.total_rows == 0
    assert task.matched_rows == 0
    assert task.unmatched_rows == 0
    assert task.failed_rows == 0
    assert task.error_message == "空表，没有数据"
    assert task.result_summary == {
        "总行数": 0,
        "成功行数": 0,
        "匹配明细数": 0,
        "未匹配行数": 0,
        "失败行数": 0,
        "汇总分组数": 0,
        "错误明细": ["空表，没有数据"],
    }
    assert upload_file.status == "processed"
    assert upload_file.error_message == "空表，没有数据"
    assert db.added_rows == []


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

    _mock_dongzhang_row_stream(
        monkeypatch,
        header=["动账时间", "动账方向", "备注", "订单实付应结"],
        rows=rows,
        period=(2026, 2),
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
async def test_execute_task_records_row_error_reasons_without_blank_detail_rows(monkeypatch) -> None:
    task = TransactionTask(id=12, file_id=22, org_id=1, user_id=2, status="queued", progress=0)
    upload_file = TransactionUploadFile(
        id=22,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
    )
    db = _TransactionAccountingSession(
        task=task,
        upload_file=upload_file,
        subjects=[],
        categories=[],
    )
    rows = [
        {
            "动账时间": datetime(2026, 3, 15, 10, 0, 0),
            "动账方向": "入账",
            "动账场景": "未知场景",
            "备注": "无法识别",
            "动账金额": "12.00",
        },
        {
            "动账时间": datetime(2026, 3, 16, 10, 0, 0),
            "动账方向": "入账",
            "动账场景": "订单结算",
            "备注": "订单结算",
            "订单实付应结": "abc",
        },
    ]
    rules = [
        make_rule(
            rule_id=1,
            priority=10,
            subject_id=1,
            category_id=11,
            transaction_direction="入账",
            transaction_scene="订单结算",
            remark_pattern="订单结算",
            amount_field="订单实付应结",
            result_direction="positive",
        )
    ]

    async def fake_load_rule_candidates(_db, *, platform_code: str | None) -> list[TransactionRuleCandidate]:
        _ = platform_code
        return rules

    _mock_dongzhang_row_stream(
        monkeypatch,
        header=["动账时间", "动账方向", "动账场景", "备注", "动账金额", "订单实付应结"],
        rows=rows,
        period=(2026, 2),
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "_load_rule_candidates",
        staticmethod(fake_load_rule_candidates),
    )

    await TransactionAccountingService.execute_task(db, task_id=12)  # type: ignore[arg-type]

    detail_rows = [item for item in db.added_rows if item.__class__.__name__ == "TransactionDetail"]

    assert task.status == "partial_success"
    assert task.matched_rows == 0
    assert task.unmatched_rows == 1
    assert task.failed_rows == 1
    assert task.result_summary["成功行数"] == 0
    assert len(detail_rows) == 0
    assert "第 2 行：未匹配分类" in (task.error_message or "")
    assert "第 3 行：取数字段 [订单实付应结] 金额无法解析" in (task.error_message or "")
    assert task.result_summary is not None
    assert task.result_summary["错误明细"] == (task.error_message or "").splitlines()
    assert any("动账场景=未知场景" in message for message in task.result_summary["错误明细"])


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

    _mock_dongzhang_row_stream(
        monkeypatch,
        header=["动账时间", "动账方向", "备注", "订单实付应结"],
        rows=[row],
        period=(2026, 2),
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


@pytest.mark.asyncio
async def test_execute_task_marks_source_file_expired_and_preserves_previous_result(monkeypatch) -> None:
    task = TransactionTask(
        id=10,
        file_id=20,
        org_id=1,
        user_id=2,
        status="success",
        progress=100,
        total_rows=9,
        matched_rows=8,
        unmatched_rows=1,
        failed_rows=0,
        result_summary={"old": True},
    )
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
        status="processed",
    )
    db = _TransactionAccountingSession(
        task=task,
        upload_file=upload_file,
        subjects=[],
        categories=[],
    )

    monkeypatch.setattr(
        TransactionAccountingService,
        "_iter_douyin_dongzhang_rows_from_oss",
        staticmethod(lambda _upload_file, period_header=None: _FakeDongzhangRowStreamContext(OSSObjectUnavailableError("missing"))),
    )

    result = await TransactionAccountingService.execute_task(db, task_id=10)  # type: ignore[arg-type]

    assert db.rollback_count == 1
    assert result.status == "expired"
    assert task.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE
    assert task.total_rows == 9
    assert task.matched_rows == 8
    assert task.unmatched_rows == 1
    assert task.failed_rows == 0
    assert task.result_summary == {"old": True}
    assert upload_file.status == "expired"
    assert upload_file.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE
