import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook, load_workbook
import pytest
from sqlalchemy import func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert

from app.models.reconciliation_checklist import (
    ReconciliationChecklistDetail,
    ReconciliationChecklistEntity,
    ReconciliationChecklistSummaryProductRow,
    ReconciliationChecklistSummaryRow,
    ReconciliationChecklistTask,
    ReconciliationChecklistUploadFile,
)
from app.services.oss_service import OSSObjectUnavailableError, SOURCE_FILE_UNAVAILABLE_MESSAGE
from app.services.partition_maintenance_service import ensure_reconciliation_checklist_partitions_for_year
from app.services.reconciliation_checklist_service import (
    CHECKLIST_HEADERS,
    ReconciliationChecklistService,
    _accounting_period,
    _canonical_header,
)


def _write_workbook(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def _row(**overrides: object) -> list[object]:
    values: dict[str, object] = {
        "平台": "douyin",
        "店铺": "示例店铺",
        "动账时间": datetime(2026, 1, 8, 10, 30, 0),
        "动账流水号": "FLOW-1",
        "商品名称": "商品A",
        "直播推广方": "直播推广方A",
        "商家": "商家A",
        "收款商家": "商家A",
        "订单金额": "100.50",
        "直播推广佣金": "10.05",
        "应付商家净额": "90.45",
    }
    values.update(overrides)
    return [values[header] for header in CHECKLIST_HEADERS]


class _ChecklistExecuteSession:
    def __init__(self, *, task: ReconciliationChecklistTask, upload_file: ReconciliationChecklistUploadFile) -> None:
        self.task = task
        self.upload_file = upload_file
        self.rollback_count = 0
        self.commit_count = 0

    async def get(self, model: type, _item_id: int):
        if model is ReconciliationChecklistTask:
            return self.task
        if model is ReconciliationChecklistUploadFile:
            return self.upload_file
        raise AssertionError(f"unexpected model: {model!r}")

    async def flush(self) -> None:
        return None

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def commit(self) -> None:
        self.commit_count += 1

    async def refresh(self, _instance: object) -> None:
        return None


class _PartitionWindowSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def scalar(self, statement: object, params: dict[str, object] | None = None):
        sql = str(statement)
        self.statements.append(sql)
        _ = params
        return None

    async def execute(self, statement: object, params: dict[str, object] | None = None):
        sql = str(statement)
        self.statements.append(sql)
        if "SELECT to_regclass" in sql:
            return SimpleNamespace(scalar=lambda: True)
        if "FROM pg_partitioned_table" in sql:
            return SimpleNamespace(scalar=lambda: True)
        if "SELECT obj_description" in sql:
            return SimpleNamespace(scalar=lambda: None)
        if "SELECT a.attname, d.description" in sql:
            return SimpleNamespace(mappings=lambda: [])
        return SimpleNamespace(scalar=lambda: None)


class _AsyncMappingStream:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.index = 0

    def mappings(self):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.rows):
            raise StopAsyncIteration
        row = self.rows[self.index]
        self.index += 1
        return row


class _ChecklistExportSession:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.stream_count = 0
        self.stream_sql: list[str] = []

    async def stream(self, statement: object):
        self.stream_count += 1
        self.stream_sql.append(str(statement.compile(dialect=postgresql.dialect())))
        return _AsyncMappingStream(self.rows)


class _ChecklistReplaceSession:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []

    async def execute(self, statement: object, params: object | None = None):
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.executed.append((sql, params))
        return SimpleNamespace(rowcount=7)


class _DashboardMetricsResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class _ChecklistDashboardSession:
    def __init__(self) -> None:
        self.scalar_results: list[object] = [3, 5, 1, 59832, Decimal("12345.67"), 2, 2]
        self.scalar_statements: list[str] = []
        self.execute_statements: list[str] = []
        self.execute_results: list[_DashboardMetricsResult] = [
            _DashboardMetricsResult([(1, 1), (3, 2)]),
            _DashboardMetricsResult([(1, Decimal("1000.50")), (3, Decimal("2345.60"))]),
            _DashboardMetricsResult(
                [
                    SimpleNamespace(merchant_id=11, merchant_name="商家A", total_order_amount=Decimal("9000.00")),
                    SimpleNamespace(merchant_id=12, merchant_name="商家B", total_order_amount=Decimal("3345.67")),
                ]
            ),
            _DashboardMetricsResult(
                [
                    SimpleNamespace(id=8, original_name="6月对账清单.xlsx", status="success", total_rows=59832, success_rows=59832, failed_rows=0, inserted_rows=59832, finished_at=datetime(2026, 6, 5, 12, 29, 40)),
                ]
            ),
        ]

    async def scalar(self, statement: object):
        self.scalar_statements.append(_compile_sql(statement))
        return self.scalar_results.pop(0)

    async def execute(self, statement: object):
        self.execute_statements.append(_compile_sql(statement))
        return self.execute_results.pop(0)


def _compile_sql(statement: object) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_reconciliation_checklist_models_define_partitioned_business_tables() -> None:
    detail_table_args = ReconciliationChecklistDetail.__table_args__
    assert isinstance(detail_table_args, tuple)
    assert detail_table_args[-1]["postgresql_partition_by"] == "RANGE (accounting_period)"

    index_names = {index.name for index in ReconciliationChecklistDetail.__table__.indexes}
    assert "uq_fin_reconciliation_checklist_business_flow" in index_names
    assert "idx_fin_reconciliation_checklist_summary" in index_names
    assert "idx_fin_reconciliation_checklist_shop_period" in index_names

    summary_index = next(index for index in ReconciliationChecklistDetail.__table__.indexes if index.name == "idx_fin_reconciliation_checklist_summary")
    assert [column.name for column in summary_index.columns] == [
        "org_id",
        "accounting_period",
        "merchant_id",
        "receipt_merchant_id",
        "live_promoter_id",
        "merchant_name",
        "receipt_merchant",
        "live_promoter",
    ]
    assert ReconciliationChecklistDetail.__table__.columns["merchant_name"].comment == "商家"
    assert ReconciliationChecklistDetail.__table__.columns["merchant_id"].comment == "商家ID"
    entity_index = next(index for index in ReconciliationChecklistEntity.__table__.indexes if index.name == "uq_fin_reconciliation_checklist_entity_name")
    assert [column.name for column in entity_index.columns] == ["org_id", "platform_code", "entity_type", "name"]
    parent_index = next(index for index in ReconciliationChecklistEntity.__table__.indexes if index.name == "idx_fin_reconciliation_checklist_entity_parent")
    assert [column.name for column in parent_index.columns] == ["parent_id"]
    assert ReconciliationChecklistEntity.__table__.columns["parent_id"].comment == "父级商家ID"
    assert ReconciliationChecklistUploadFile.__tablename__ == "fin_reconciliation_checklist_upload_files"
    assert ReconciliationChecklistTask.__tablename__ == "fin_reconciliation_checklist_tasks"
    assert ReconciliationChecklistDetail.__tablename__ == "fin_reconciliation_checklist_details"
    assert ReconciliationChecklistEntity.__tablename__ == "fin_reconciliation_checklist_entities"
    assert "raw_row" not in ReconciliationChecklistDetail.__table__.columns


def test_reconciliation_checklist_models_define_preaggregated_summary_tables() -> None:
    assert ReconciliationChecklistSummaryRow.__tablename__ == "fin_reconciliation_checklist_summary_rows"
    assert ReconciliationChecklistSummaryProductRow.__tablename__ == "fin_reconciliation_checklist_summary_product_rows"
    assert ReconciliationChecklistSummaryRow.__table_args__[-1]["postgresql_partition_by"] == "RANGE (accounting_period)"
    assert ReconciliationChecklistSummaryProductRow.__table_args__[-1]["postgresql_partition_by"] == "RANGE (accounting_period)"
    assert [column.name for column in ReconciliationChecklistSummaryRow.__table__.primary_key.columns] == ["id", "accounting_period"]
    assert [column.name for column in ReconciliationChecklistSummaryProductRow.__table__.primary_key.columns] == ["id", "accounting_period"]

    summary_columns = ReconciliationChecklistSummaryRow.__table__.columns
    product_columns = ReconciliationChecklistSummaryProductRow.__table__.columns
    for column_name in [
        "org_id",
        "shop_id",
        "accounting_period",
        "merchant_id",
        "receipt_merchant_id",
        "live_promoter_id",
        "product_quantity",
        "total_order_amount",
        "total_live_commission",
        "total_merchant_net_amount",
    ]:
        assert column_name in summary_columns
        assert column_name in product_columns
    assert "product_name" in product_columns


def test_checklist_header_alias_accepts_template_variant() -> None:
    assert _canonical_header("动帐流水号") == "动账流水号"
    assert _canonical_header(" 动账流水号 ") == "动账流水号"


def test_entity_upsert_conflict_target_matches_partial_unique_index() -> None:
    stmt = insert(ReconciliationChecklistEntity).values(
        [
            {
                "org_id": 1,
                "platform_code": "douyin",
                "entity_type": "merchant",
                "name": "商家A",
                "status": "active",
                "source": "auto",
                "last_seen_period": 202606,
            }
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["org_id", "platform_code", "entity_type", "name"],
        index_where=text("is_deleted = false"),
        set_={"updated_at": func.now()},
    )

    sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (org_id, platform_code, entity_type, name) WHERE is_deleted = false" in sql


def test_parse_file_extracts_period_from_transaction_time_and_money(tmp_path: Path) -> None:
    file_path = tmp_path / "checklist.xlsx"
    headers = CHECKLIST_HEADERS.copy()
    headers[headers.index("动账流水号")] = "动帐流水号"
    _write_workbook(
        file_path,
        headers,
        [
            _row(动账流水号="FLOW-1", 订单金额="1,000.50", 直播推广佣金="100.05", 应付商家净额="900.45"),
            _row(动账时间="2026-02-01 09:00:00", 动账流水号="FLOW-2", 商品名称="商品B", 订单金额=200, 直播推广佣金=20, 应付商家净额=180),
        ],
    )

    result = ReconciliationChecklistService.parse_file(str(file_path))

    assert result["total_rows"] == 2
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert result["fatal_error"] is False
    assert [
        (
            row["accounting_year"],
            row["accounting_month"],
            row["accounting_period"],
            row["transaction_flow_no"],
            row["merchant_name"],
            row["order_amount"],
            row["live_commission"],
            row["merchant_net_amount"],
        )
        for row in result["rows"]
    ] == [
        (2026, 1, 202601, "FLOW-1", "商家A", Decimal("1000.50"), Decimal("100.05"), Decimal("900.45")),
        (2026, 2, 202602, "FLOW-2", "商家A", Decimal("200.00"), Decimal("20.00"), Decimal("180.00")),
    ]


def test_parse_file_accepts_legacy_gmv_header_alias(tmp_path: Path) -> None:
    file_path = tmp_path / "legacy_gmv.xlsx"
    headers = CHECKLIST_HEADERS.copy()
    headers[headers.index("订单金额")] = "GMV"
    _write_workbook(file_path, headers, [_row(订单金额="88.66")])

    result = ReconciliationChecklistService.parse_file(str(file_path))

    assert result["success_rows"] == 1
    assert result["rows"][0]["order_amount"] == Decimal("88.66")


def test_parse_file_marks_missing_required_header_as_fatal(tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.xlsx"
    _write_workbook(file_path, ["平台", "店铺"], [["douyin", "示例店铺"]])

    result = ReconciliationChecklistService.parse_file(str(file_path))

    assert result["fatal_error"] is True
    assert result["failed_rows"] == 1
    assert "缺少对账清单必要表头" in result["errors"][0]


def test_parse_file_marks_invalid_transaction_time_as_row_error(tmp_path: Path) -> None:
    file_path = tmp_path / "bad_time.xlsx"
    _write_workbook(file_path, CHECKLIST_HEADERS, [_row(动账时间="bad-time")])

    result = ReconciliationChecklistService.parse_file(str(file_path))

    assert result["total_rows"] == 1
    assert result["success_rows"] == 0
    assert result["failed_rows"] == 1
    assert result["fatal_error"] is False
    assert "动账时间无法解析" in result["errors"][0]


def test_accounting_period_validates_month() -> None:
    assert _accounting_period(2026, 1) == 202601
    with pytest.raises(ValueError, match="月份"):
        _accounting_period(2026, 13)


@pytest.mark.asyncio
async def test_replace_detail_rows_hard_deletes_only_covered_scopes_and_bulk_inserts() -> None:
    rows = [
        ReconciliationChecklistDetail(
            task_id=1,
            file_id=2,
            org_id=3,
            shop_id=4,
            platform_code="douyin",
            shop_name="店铺A",
            accounting_year=2026,
            accounting_month=1,
            accounting_period=202601,
            source_row_number=1,
            transaction_time=datetime(2026, 1, 8, 10, 30, 0),
            transaction_flow_no="FLOW-1",
            product_name="商品A",
            live_promoter_id=11,
            merchant_id=12,
            receipt_merchant_id=13,
            live_promoter="推广方A",
            merchant_name="商家A",
            receipt_merchant="收款商家A",
            order_amount=Decimal("100.00"),
            live_commission=Decimal("10.00"),
            merchant_net_amount=Decimal("90.00"),
        ),
        ReconciliationChecklistDetail(
            task_id=1,
            file_id=2,
            org_id=3,
            shop_id=5,
            platform_code="douyin",
            shop_name="店铺B",
            accounting_year=2026,
            accounting_month=1,
            accounting_period=202601,
            source_row_number=2,
            transaction_time=datetime(2026, 1, 8, 11, 30, 0),
            transaction_flow_no="FLOW-2",
            product_name="商品B",
            live_promoter_id=11,
            merchant_id=12,
            receipt_merchant_id=13,
            live_promoter="推广方A",
            merchant_name="商家A",
            receipt_merchant="收款商家A",
            order_amount=Decimal("200.00"),
            live_commission=Decimal("20.00"),
            merchant_net_amount=Decimal("180.00"),
        ),
    ]
    session = _ChecklistReplaceSession()

    inserted_rows, deleted_rows, scopes = await ReconciliationChecklistService._replace_detail_rows(session, rows)  # type: ignore[arg-type]

    assert inserted_rows == 2
    assert deleted_rows == 7
    assert scopes == [(3, 202601, "douyin", 4), (3, 202601, "douyin", 5)]
    lock_statements = session.executed[:2]
    delete_sql, delete_params = session.executed[2]
    insert_sql, insert_params = session.executed[3]
    assert all("pg_advisory_xact_lock" in sql for sql, _params in lock_statements)
    assert delete_sql.startswith("DELETE FROM fin_reconciliation_checklist_details")
    assert "org_id" in delete_sql
    assert "accounting_period" in delete_sql
    assert "platform_code" in delete_sql
    assert "shop_id" in delete_sql
    assert "UPDATE fin_reconciliation_checklist_details" not in delete_sql
    assert insert_sql.startswith("INSERT INTO fin_reconciliation_checklist_details")
    assert isinstance(insert_params, list)
    assert len(insert_params) == 2
    assert "raw_row" not in insert_params[0]


@pytest.mark.asyncio
async def test_ensure_reconciliation_checklist_partitions_for_year_creates_full_year_window() -> None:
    session = _PartitionWindowSession()

    result = await ensure_reconciliation_checklist_partitions_for_year(session, year=2026)  # type: ignore[arg-type]

    detail_statements = [sql for sql in session.statements if "CREATE TABLE IF NOT EXISTS fin_reconciliation_checklist_details_" in sql]
    summary_statements = [sql for sql in session.statements if "CREATE TABLE IF NOT EXISTS fin_reconciliation_checklist_summary_rows_" in sql]
    product_statements = [sql for sql in session.statements if "CREATE TABLE IF NOT EXISTS fin_reconciliation_checklist_summary_product_rows_" in sql]
    assert result == {"start_period": 202601, "end_period": 202612, "year": 2026}
    assert len(detail_statements) == 12
    assert len(summary_statements) == 12
    assert len(product_statements) == 12
    assert any("fin_reconciliation_checklist_details_202601" in sql for sql in detail_statements)
    assert any("fin_reconciliation_checklist_summary_rows_202601" in sql for sql in summary_statements)
    assert any("fin_reconciliation_checklist_summary_product_rows_202601" in sql for sql in product_statements)
    assert any("FOR VALUES FROM (202612) TO (202701)" in sql for sql in product_statements)


@pytest.mark.asyncio
async def test_execute_task_precreates_current_year_partition_window_once(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="finengine.reconciliation_checklist")
    task = ReconciliationChecklistTask(
        id=1,
        file_id=2,
        org_id=3,
        user_id=4,
        status="queued",
        progress=0,
    )
    upload_file = ReconciliationChecklistUploadFile(
        id=2,
        org_id=3,
        user_id=4,
        original_name="对账清单.xlsx",
        oss_key="oss-key",
        status="uploaded",
    )
    session = _ChecklistExecuteSession(task=task, upload_file=upload_file)
    ensure_calls: list[int] = []

    monkeypatch.setattr(
        "app.services.reconciliation_checklist_service.oss_service.download_to_temp",
        lambda *_args, **_kwargs: None,
    )

    async def fake_ensure_year(db, *, year: int) -> dict[str, int]:
        assert db is session
        ensure_calls.append(year)
        return {"start_period": year * 100 + 1, "end_period": year * 100 + 12, "year": year}

    async def fake_persist_task_result(*_args, **_kwargs) -> dict:
        return {
            "总行数": 0,
            "成功行数": 0,
            "失败行数": 0,
            "新增行数": 0,
            "更新行数": 0,
        }

    monkeypatch.setattr(
        "app.services.reconciliation_checklist_service.ensure_reconciliation_checklist_partitions_for_year",
        fake_ensure_year,
    )
    monkeypatch.setattr(
        ReconciliationChecklistService,
        "persist_task_result",
        staticmethod(fake_persist_task_result),
    )

    result = await ReconciliationChecklistService.execute_task(session, task_id=1)  # type: ignore[arg-type]

    assert ensure_calls == [datetime.now().year]
    assert result.status == "success"
    assert upload_file.status == "processed"
    assert sum("reconciliation_checklist.task_perf" in record.message for record in caplog.records) == 1


@pytest.mark.asyncio
async def test_execute_task_commits_running_state_before_heavy_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    task = ReconciliationChecklistTask(
        id=1,
        file_id=2,
        org_id=3,
        user_id=4,
        status="queued",
        progress=0,
    )
    upload_file = ReconciliationChecklistUploadFile(
        id=2,
        org_id=3,
        user_id=4,
        original_name="对账清单.xlsx",
        oss_key="oss-key",
        status="uploaded",
    )
    session = _ChecklistExecuteSession(task=task, upload_file=upload_file)

    async def fake_ensure_year(*_args, **_kwargs) -> dict[str, int]:
        assert session.commit_count == 1
        assert task.status == "running"
        assert task.progress == 5
        assert task.started_at is not None
        return {"start_period": 202601, "end_period": 202612, "year": 2026}

    async def fake_persist_task_result(*_args, **_kwargs) -> dict:
        return {
            "总行数": 0,
            "成功行数": 0,
            "失败行数": 0,
            "新增行数": 0,
            "更新行数": 0,
        }

    monkeypatch.setattr(
        "app.services.reconciliation_checklist_service.ensure_reconciliation_checklist_partitions_for_year",
        fake_ensure_year,
    )
    monkeypatch.setattr(
        "app.services.reconciliation_checklist_service.oss_service.download_to_temp",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ReconciliationChecklistService,
        "persist_task_result",
        staticmethod(fake_persist_task_result),
    )

    result = await ReconciliationChecklistService.execute_task(session, task_id=1)  # type: ignore[arg-type]

    assert session.commit_count == 1
    assert result.status == "success"


@pytest.mark.asyncio
async def test_execute_task_marks_source_file_expired_and_preserves_previous_result(monkeypatch: pytest.MonkeyPatch) -> None:
    task = ReconciliationChecklistTask(
        id=1,
        file_id=2,
        org_id=3,
        user_id=4,
        status="success",
        progress=100,
        total_rows=8,
        success_rows=8,
        failed_rows=0,
        inserted_rows=5,
        updated_rows=3,
        result_summary={"old": True},
    )
    upload_file = ReconciliationChecklistUploadFile(
        id=2,
        org_id=3,
        user_id=4,
        original_name="对账清单.xlsx",
        oss_key="oss-key",
        status="processed",
    )
    session = _ChecklistExecuteSession(task=task, upload_file=upload_file)

    async def fake_ensure_year(*_args, **_kwargs) -> dict[str, int]:
        return {"start_period": 202601, "end_period": 202612, "year": 2026}

    monkeypatch.setattr(
        "app.services.reconciliation_checklist_service.ensure_reconciliation_checklist_partitions_for_year",
        fake_ensure_year,
    )
    monkeypatch.setattr(
        "app.services.reconciliation_checklist_service.oss_service.download_to_temp",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSSObjectUnavailableError("missing")),
    )

    result = await ReconciliationChecklistService.execute_task(session, task_id=1)  # type: ignore[arg-type]

    assert session.rollback_count == 1
    assert result.status == "expired"
    assert task.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE
    assert task.total_rows == 8
    assert task.success_rows == 8
    assert task.failed_rows == 0
    assert task.inserted_rows == 5
    assert task.updated_rows == 3
    assert task.result_summary == {"old": True}
    assert upload_file.status == "expired"
    assert upload_file.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE


@pytest.mark.asyncio
async def test_persist_task_result_emits_perf_log(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="finengine.reconciliation_checklist")
    task = ReconciliationChecklistTask(
        id=1,
        file_id=2,
        org_id=3,
        user_id=4,
        status="running",
        progress=5,
    )
    upload_file = ReconciliationChecklistUploadFile(
        id=2,
        org_id=3,
        user_id=4,
        original_name="对账清单.xlsx",
        oss_key="oss-key",
        status="uploaded",
    )
    session = _ChecklistExecuteSession(task=task, upload_file=upload_file)

    monkeypatch.setattr(
        ReconciliationChecklistService,
        "parse_file",
        staticmethod(
            lambda _path: {
                "rows": [],
                "total_rows": 0,
                "success_rows": 0,
                "failed_rows": 0,
                "errors": [],
                "warnings": [],
            }
        ),
    )

    summary = await ReconciliationChecklistService.persist_task_result(
        session,  # type: ignore[arg-type]
        task=task,
        upload_file=upload_file,
        file_path="/tmp/checklist.xlsx",
    )

    assert summary["总行数"] == 0
    assert summary["原始明细行数"] == 0
    assert summary["去重后明细行数"] == 0
    assert summary["覆盖范围数"] == 0
    assert summary["涉及年月"] == []
    assert summary["重建汇总行范围数"] == 0
    assert sum("reconciliation_checklist.persist_task_result_perf" in record.message for record in caplog.records) == 1


@pytest.mark.asyncio
async def test_export_summary_uses_merchant_dimension_and_bordered_compact_total(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "export.xlsx"
    summary_rows = [
        {
            "key": "1:202601:商家A:收款商家A:直播推广方A",
            "org_id": 1,
            "org_name": "组织A",
            "accounting_year": 2026,
            "accounting_month": 1,
            "accounting_period": 202601,
            "merchant_id": 11,
            "live_promoter_id": 12,
            "receipt_merchant_id": 13,
            "merchant_name": "商家A",
            "receipt_merchant": "收款商家A",
            "live_promoter": "直播推广方A",
            "product_quantity": 1,
            "total_order_amount": Decimal("100.00"),
            "total_live_commission": Decimal("10.00"),
            "total_merchant_net_amount": Decimal("90.00"),
        }
    ]
    detail_rows = [
        {
            "summary_key": summary_rows[0]["key"],
            "product_name": "商品A",
            "product_quantity": 1,
            "total_order_amount": Decimal("100.00"),
            "total_live_commission": Decimal("10.00"),
            "total_merchant_net_amount": Decimal("90.00"),
        }
    ]
    session = _ChecklistExportSession(detail_rows)

    async def fake_list_summary(*args, **kwargs):
        return summary_rows, 1

    monkeypatch.setattr(ReconciliationChecklistService, "list_summary", staticmethod(fake_list_summary))

    row_count = await ReconciliationChecklistService.export_summary_to_file(
        session,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),  # type: ignore[arg-type]
        output_path=output_path,
    )

    workbook = load_workbook(output_path)
    try:
        worksheet = workbook.active
        assert row_count == 1
        assert worksheet.title.startswith("2026年1月_商家A")
        assert worksheet["A2"].value == "商家"
        assert worksheet["B2"].value == "商家A"
        assert worksheet["A3"].value == "收款商家"
        assert worksheet["B3"].value == "收款商家A"
        assert worksheet["A4"].value == "直播编号"
        assert worksheet["A6"].value == "总计"
        assert worksheet["A5"].value == 1
        assert worksheet["A1"].border.left.style == "thin"
        assert worksheet["E6"].border.bottom.style == "thin"
        assert session.stream_count == 1
    finally:
        workbook.close()


@pytest.mark.asyncio
async def test_export_summary_streams_grouped_details_without_per_summary_queries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "stream_export.xlsx"
    summary_rows = [
        {
            "key": "1:202601:11:31:21:商家A:收款商家A:直播推广方A",
            "org_id": 1,
            "org_name": "组织A",
            "accounting_year": 2026,
            "accounting_month": 1,
            "accounting_period": 202601,
            "merchant_id": 11,
            "live_promoter_id": 21,
            "receipt_merchant_id": 31,
            "merchant_name": "商家A",
            "receipt_merchant": "收款商家A",
            "live_promoter": "直播推广方A",
            "product_quantity": 2,
            "total_order_amount": Decimal("300.00"),
            "total_live_commission": Decimal("30.00"),
            "total_merchant_net_amount": Decimal("270.00"),
        },
        {
            "key": "1:202601:12:32:22:商家B:收款商家B:直播推广方B",
            "org_id": 1,
            "org_name": "组织A",
            "accounting_year": 2026,
            "accounting_month": 1,
            "accounting_period": 202601,
            "merchant_id": 12,
            "live_promoter_id": 22,
            "receipt_merchant_id": 32,
            "merchant_name": "商家B",
            "receipt_merchant": "收款商家B",
            "live_promoter": "直播推广方B",
            "product_quantity": 1,
            "total_order_amount": Decimal("80.00"),
            "total_live_commission": Decimal("8.00"),
            "total_merchant_net_amount": Decimal("72.00"),
        },
    ]
    detail_rows = [
        {
            "summary_key": summary_rows[0]["key"],
            "product_name": "商品A",
            "product_quantity": 1,
            "total_order_amount": Decimal("100.00"),
            "total_live_commission": Decimal("10.00"),
            "total_merchant_net_amount": Decimal("90.00"),
        },
        {
            "summary_key": summary_rows[0]["key"],
            "product_name": "商品B",
            "product_quantity": 1,
            "total_order_amount": Decimal("200.00"),
            "total_live_commission": Decimal("20.00"),
            "total_merchant_net_amount": Decimal("180.00"),
        },
        {
            "summary_key": summary_rows[1]["key"],
            "product_name": "商品C",
            "product_quantity": 1,
            "total_order_amount": Decimal("80.00"),
            "total_live_commission": Decimal("8.00"),
            "total_merchant_net_amount": Decimal("72.00"),
        },
    ]
    session = _ChecklistExportSession(detail_rows)

    async def fake_list_summary(*args, **kwargs):
        return summary_rows, 2

    async def fail_list_summary_details(*args, **kwargs):
        raise AssertionError("export should stream all grouped detail rows instead of querying each summary")

    monkeypatch.setattr(ReconciliationChecklistService, "list_summary", staticmethod(fake_list_summary))
    monkeypatch.setattr(ReconciliationChecklistService, "list_summary_details", staticmethod(fail_list_summary_details))

    row_count = await ReconciliationChecklistService.export_summary_to_file(
        session,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),  # type: ignore[arg-type]
        output_path=output_path,
    )

    workbook = load_workbook(output_path)
    try:
        assert session.stream_count == 1
        assert "fin_reconciliation_checklist_summary_product_rows" in session.stream_sql[0]
        assert "fin_reconciliation_checklist_details" not in session.stream_sql[0]
        assert row_count == 3
        assert workbook.sheetnames == ["2026年1月_商家A", "2026年1月_商家B"]
        assert workbook["2026年1月_商家A"]["B5"].value == "商品A"
        assert workbook["2026年1月_商家A"]["B6"].value == "商品B"
        assert workbook["2026年1月_商家B"]["B5"].value == "商品C"
    finally:
        workbook.close()


@pytest.mark.asyncio
async def test_export_summary_forwards_entity_id_filters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "export_ids.xlsx"

    async def fake_list_summary(*args, **kwargs):
        assert kwargs["merchant_ids"] == "11,12"
        assert kwargs["live_promoter_ids"] == "21"
        assert kwargs["receipt_merchant_ids"] == "31"
        return [
            {
                "key": "1:202601:11:31:21:商家A:收款商家A:直播推广方A",
                "org_id": 1,
                "org_name": "组织A",
                "accounting_year": 2026,
                "accounting_month": 1,
                "accounting_period": 202601,
                "merchant_id": 11,
                "live_promoter_id": 21,
                "receipt_merchant_id": 31,
                "merchant_name": "商家A",
                "receipt_merchant": "收款商家A",
                "live_promoter": "直播推广方A",
                "product_quantity": 1,
                "total_order_amount": Decimal("100.00"),
                "total_live_commission": Decimal("10.00"),
                "total_merchant_net_amount": Decimal("90.00"),
            }
        ], 1

    detail_rows = [
        {
            "summary_key": "1:202601:11:31:21:商家A:收款商家A:直播推广方A",
            "product_name": "商品A",
            "product_quantity": 1,
            "total_order_amount": Decimal("100.00"),
            "total_live_commission": Decimal("10.00"),
            "total_merchant_net_amount": Decimal("90.00"),
        }
    ]
    session = _ChecklistExportSession(detail_rows)

    async def fake_iter_export_summary_detail_rows(*args, **kwargs):
        assert kwargs["merchant_ids"] == "11,12"
        assert kwargs["live_promoter_ids"] == "21"
        assert kwargs["receipt_merchant_ids"] == "31"
        for row in detail_rows:
            yield row

    monkeypatch.setattr(ReconciliationChecklistService, "list_summary", staticmethod(fake_list_summary))
    monkeypatch.setattr(
        ReconciliationChecklistService,
        "_iter_export_summary_detail_rows",
        staticmethod(fake_iter_export_summary_detail_rows),
    )

    row_count = await ReconciliationChecklistService.export_summary_to_file(
        session,  # type: ignore[arg-type]
        user=SimpleNamespace(role="admin", org_id=1),  # type: ignore[arg-type]
        output_path=output_path,
        merchant_ids="11,12",
        live_promoter_ids="21",
        receipt_merchant_ids="31",
    )

    assert row_count == 1


@pytest.mark.asyncio
async def test_dashboard_metrics_uses_processed_checklist_data_and_full_year_months() -> None:
    session = _ChecklistDashboardSession()

    metrics = await ReconciliationChecklistService.get_dashboard_metrics(
        session,  # type: ignore[arg-type]
        user=SimpleNamespace(role="org_admin", org_id=8),  # type: ignore[arg-type]
        year=2026,
    )

    assert metrics["processed_task_count"] == 3
    assert metrics["total_task_count"] == 5
    assert metrics["failed_task_count"] == 1
    assert metrics["total_rows"] == 59832
    assert metrics["total_order_amount"] == Decimal("12345.67")
    assert metrics["merchant_count"] == 2
    assert metrics["covered_month_count"] == 2
    assert metrics["completion_rate"] == Decimal("60.00")
    assert metrics["year"] == 2026
    assert metrics["monthly_task_counts"] == [
        {"month": 1, "task_count": 1},
        {"month": 2, "task_count": 0},
        {"month": 3, "task_count": 2},
        {"month": 4, "task_count": 0},
        {"month": 5, "task_count": 0},
        {"month": 6, "task_count": 0},
        {"month": 7, "task_count": 0},
        {"month": 8, "task_count": 0},
        {"month": 9, "task_count": 0},
        {"month": 10, "task_count": 0},
        {"month": 11, "task_count": 0},
        {"month": 12, "task_count": 0},
    ]
    assert metrics["monthly_order_amounts"] == [
        {"month": 1, "total_order_amount": Decimal("1000.50")},
        {"month": 2, "total_order_amount": Decimal("0.00")},
        {"month": 3, "total_order_amount": Decimal("2345.60")},
        {"month": 4, "total_order_amount": Decimal("0.00")},
        {"month": 5, "total_order_amount": Decimal("0.00")},
        {"month": 6, "total_order_amount": Decimal("0.00")},
        {"month": 7, "total_order_amount": Decimal("0.00")},
        {"month": 8, "total_order_amount": Decimal("0.00")},
        {"month": 9, "total_order_amount": Decimal("0.00")},
        {"month": 10, "total_order_amount": Decimal("0.00")},
        {"month": 11, "total_order_amount": Decimal("0.00")},
        {"month": 12, "total_order_amount": Decimal("0.00")},
    ]
    assert metrics["top_merchants"] == [
        {"merchant_id": 11, "merchant_name": "商家A", "total_order_amount": Decimal("9000.00")},
        {"merchant_id": 12, "merchant_name": "商家B", "total_order_amount": Decimal("3345.67")},
    ]
    assert metrics["recent_tasks"] == [
        {
            "id": 8,
            "original_name": "6月对账清单.xlsx",
            "status": "success",
            "total_rows": 59832,
            "success_rows": 59832,
            "failed_rows": 0,
            "inserted_rows": 59832,
            "finished_at": datetime(2026, 6, 5, 12, 29, 40),
        }
    ]

    joined_scalar_sql = "\n".join(session.scalar_statements)
    assert "fin_reconciliation_checklist_tasks.status IN ('success', 'partial_success')" in joined_scalar_sql
    assert "fin_reconciliation_checklist_details.order_amount" in joined_scalar_sql
    assert "count(distinct(fin_reconciliation_checklist_details.merchant_id))" in joined_scalar_sql
    assert "receipt_merchant_id" not in session.scalar_statements[5]
    assert "fin_reconciliation_checklist_tasks.org_id IN (8)" in joined_scalar_sql
