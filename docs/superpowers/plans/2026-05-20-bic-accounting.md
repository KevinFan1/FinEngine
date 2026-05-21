# BIC核算 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new independent `BIC核算` module for Douyin BIC reporting while moving upload entry points back to the main upload center and keeping the existing transaction-accounting flow intact.

**Architecture:** Reuse the existing upload center for file ingestion and classification, but route Douyin files into two explicit processing paths: `动账` and `BIC`. Keep BIC as a separate frontend menu group with its own task/detail/report views and API surface, while sharing common UI helpers and upload infrastructure where it reduces duplication without coupling behavior.

**Tech Stack:** Vue 3 + Element Plus frontend, FastAPI backend, SQLAlchemy async ORM, Celery workers, openpyxl/xlrd CSV/XLS parsing, existing FinEngine upload and task infrastructure.

---

### Task 1: Split upload entry points and wire BIC file detection

**Files:**
- Modify: `frontend/src/layouts/DefaultLayout.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/dashboard/index.vue`
- Modify: `backend/scripts/seed_file_specs.py`
- Modify: `backend/app/api/v1/file_specs.py`
- Modify: `backend/app/tasks/processors/douyin.py`
- Modify: `backend/app/tasks/processors/__init__.py`
- Modify: `backend/app/tasks/celery_app.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Add a failing frontend expectation for the menu move**

```typescript
// frontend/src/layouts/DefaultLayout.vue should no longer render an upload child
// under 动账资金核算, and the main Upload menu should remain the primary entry.
```

- [ ] **Step 2: Add a failing backend expectation for Douyin BIC dispatch**

```python
# backend/app/tests/test_douyin_processor.py
def test_douyin_bic_routes_to_bic_processor(tmp_path: Path) -> None:
    file_path = tmp_path / "26年05月_类别_抖音店铺.xlsx"
    _write_workbook(file_path, DOUYIN_BIC_HEADERS, [_row(DOUYIN_BIC_HEADERS, 费用项="质检费(通过)", 结算金额="10")])
    result = douyin_processor.process(str(file_path), shop_name="抖音店铺", type_code="bic")
    assert result["groups"]["抖音店铺|2026|5"]["bic"] == Decimal("10")
```

- [ ] **Step 3: Run the targeted tests and confirm they fail for the missing BIC path**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_douyin_processor.py -k bic
```
Expected: fail because BIC logic is still coupled to the old simple monthly sum path.

- [ ] **Step 4: Implement the minimal routing changes**

```python
# backend/app/tasks/processors/__init__.py
from app.tasks.processors.bic import bic_processor
PLATFORM_PROCESSORS = {"douyin": douyin_processor, "抖店": douyin_processor, "douyin-bic": bic_processor, ...}
```

```python
# backend/app/tasks/celery_app.py
# when parsed_type is "BIC", dispatch to the BIC processor path instead of the legacy Douyin monthly sum behavior
```

- [ ] **Step 5: Update file spec seed data for BIC type**

```python
# backend/scripts/seed_file_specs.py
{
    "platform_code": "douyin",
    "type_code": "bic",
    "name": "抖音BIC",
    "match_threshold": 5,
    "headers": [
        "结算单号","订单码","关联订单号","关联运单号","费用项","服务商","QIC仓","结算金额","计费参数","计费完成时间","业务节点","业务发生时间","结算时间","状态","动账账户","动账流水号","备注","是否木带宝","是否子单",
    ],
}
```

- [ ] **Step 6: Rerun the tests and confirm the new BIC dispatch passes**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_douyin_processor.py -k bic
```
Expected: pass.

### Task 2: Create the BIC backend module and API surface

**Files:**
- Create: `backend/app/models/bic_accounting.py`
- Create: `backend/app/schemas/bic_accounting.py`
- Create: `backend/app/services/bic_accounting_service.py`
- Create: `backend/app/api/v1/bic_accounting.py`
- Create: `backend/app/tasks/bic_accounting.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write backend tests for BIC parse and aggregation rules**

```python
# backend/app/tests/test_bic_accounting_service.py
def test_bic_filename_parse_uses_year_month_and_shop() -> None:
    assert BicAccountingService.parse_filename("26年05月_BIC_抖音店铺.xlsx") == {"year": 2026, "month": 5, "shop": "抖音店铺"}

def test_bic_aggregates_only_quality_inspection_fees() -> None:
    rows = [
        {"平台": "抖音", "店铺": "抖音店铺", "年月": "2026-05", "QIC仓": "A", "费用项": "质检费(通过)", "结算金额": "12"},
        {"平台": "抖音", "店铺": "抖音店铺", "年月": "2026-05", "QIC仓": "A", "费用项": "其他", "结算金额": "99"},
    ]
    assert BicAccountingService.sum_detail_amount(rows) == Decimal("12")
```

- [ ] **Step 2: Run the tests and verify the new service does not exist yet**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_bic_accounting_service.py
```
Expected: fail because the module is not implemented yet.

- [ ] **Step 3: Implement the BIC tables, schemas, service, and task runner**

```python
# backend/app/models/bic_accounting.py
class BicUploadFile(...): ...
class BicTask(...): ...
class BicDetail(...): ...
class BicSummary(...): ...
```

```python
# backend/app/services/bic_accounting_service.py
class BicAccountingService:
    @staticmethod
    def parse_filename(filename: str) -> dict[str, int | str]: ...
    @staticmethod
    async def init_upload(...): ...
    @staticmethod
    async def upload_callback(...): ...
    @staticmethod
    async def list_tasks(...): ...
    @staticmethod
    async def list_details(...): ...
    @staticmethod
    async def list_reports(...): ...
    @staticmethod
    async def export_details(...): ...
    @staticmethod
    async def export_reports(...): ...
```

- [ ] **Step 4: Expose the BIC API routes**

```python
# backend/app/api/v1/bic_accounting.py
@router.get("/upload-init")
@router.post("/upload-callback")
@router.get("/tasks")
@router.get("/details")
@router.get("/details/export")
@router.get("/summary")
@router.get("/summary/export")
```

- [ ] **Step 5: Register the router**

```python
# backend/app/api/v1/router.py
api_router.include_router(bic_accounting.router, prefix="/bic-accounting", tags=["BIC核算"])
```

- [ ] **Step 6: Run the backend tests until the service and API tests pass**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_bic_accounting_service.py app/tests/test_douyin_processor.py -k bic
```
Expected: pass.

### Task 3: Build the BIC frontend module and move upload entry points

**Files:**
- Create: `frontend/src/api/bicAccounting.ts`
- Create: `frontend/src/views/bic-accounting/upload.vue`
- Create: `frontend/src/views/bic-accounting/tasks.vue`
- Create: `frontend/src/views/bic-accounting/details.vue`
- Create: `frontend/src/views/bic-accounting/report.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/DefaultLayout.vue`
- Modify: `frontend/src/views/dashboard/index.vue`
- Modify: `frontend/src/views/upload/index.vue`
- Modify: `frontend/src/views/transaction-accounting/upload.vue`

- [ ] **Step 1: Add frontend tests for the new menu and removed upload child**

```typescript
// verify the sidebar now shows BIC核算 as a separate top-level menu
// and that the upload child sits under the main Upload center only
```

- [ ] **Step 2: Implement the BIC API client**

```typescript
// frontend/src/api/bicAccounting.ts should mirror the transactionAccounting client
// but use /bic-accounting/* endpoints and BIC-specific payload types
```

- [ ] **Step 3: Clone the transaction-accounting pages into BIC pages and retarget API imports**

```vue
<!-- frontend/src/views/bic-accounting/report.vue -->
<!-- reuse the same layout, filters, and export controls, but bind to BIC summary APIs -->
```

- [ ] **Step 4: Remove the upload child from the old transaction-accounting menu**

```vue
<!-- frontend/src/layouts/DefaultLayout.vue -->
// keep 动账核算 as task/details/report only
// leave upload at /upload as the main upload center
```

- [ ] **Step 5: Make the main upload center the only upload entry point**

```vue
<!-- frontend/src/views/dashboard/index.vue -->
// route primary upload button to /upload only
```

- [ ] **Step 6: Run the frontend build and verify the route tree compiles**

Run:
```bash
cd frontend && npm run build
```
Expected: pass with the new BIC routes and existing upload route intact.

### Task 4: Add BIC-specific tests and export coverage

**Files:**
- Create: `backend/app/tests/test_bic_accounting_api.py`
- Create: `backend/app/tests/test_bic_accounting_export.py`
- Modify: `backend/app/tests/test_douyin_processor.py`

- [ ] **Step 1: Write export tests for BIC details and BIC reports**

```python
def test_bic_detail_export_filters_by_platform_shop_year_month_qic() -> None: ...
def test_bic_report_export_aggregates_detail_rows() -> None: ...
```

- [ ] **Step 2: Run the export tests and verify they fail before implementation**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_bic_accounting_api.py app/tests/test_bic_accounting_export.py
```
Expected: fail until the export endpoints exist.

- [ ] **Step 3: Implement the BIC export endpoints and final aggregation logic**

```python
# detail export groups by platform, shop, year-month, QIC仓
# report export groups by platform, shop, year-month
# both use only rows where 费用项 == "质检费(通过)"
```

- [ ] **Step 4: Rerun the targeted backend tests**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_bic_accounting_api.py app/tests/test_bic_accounting_export.py app/tests/test_douyin_processor.py -k bic
```
Expected: pass.

### Task 5: Final verification

**Files:**
- All modified files from Tasks 1-4

- [ ] **Step 1: Run backend test subset for the new flow**

Run:
```bash
cd backend && uv run pytest -q app/tests/test_douyin_processor.py app/tests/test_bic_accounting_service.py app/tests/test_bic_accounting_api.py app/tests/test_bic_accounting_export.py
```

- [ ] **Step 2: Run frontend build**

Run:
```bash
cd frontend && npm run build
```

- [ ] **Step 3: Spot-check the upload center and BIC routes in the browser**

Open:
```text
/upload
/transaction-tasks
/bic-accounting/tasks
/bic-accounting/report
```

- [ ] **Step 4: Commit the implementation**

```bash
git add backend frontend docs/superpowers/plans/2026-05-20-bic-accounting.md
git commit -m "feat: add bic accounting module"
```
