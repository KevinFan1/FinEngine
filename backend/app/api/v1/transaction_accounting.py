"""Independent transaction-accounting API."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.deps import get_current_user, require_superadmin
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.transaction_accounting import (
    TransactionAnnualSummaryOut,
    TransactionCashFlowItemOut,
    TransactionCategoryCreate,
    TransactionCategoryOut,
    TransactionCategoryUpdate,
    TransactionDetailOut,
    TransactionMajorCategoryCreate,
    TransactionMajorCategoryOut,
    TransactionMajorCategoryUpdate,
    TransactionRuleCreate,
    TransactionRuleOut,
    TransactionRuleUpdate,
    TransactionSubjectCreate,
    TransactionSubjectOut,
    TransactionSubjectUpdate,
    TransactionSummaryOut,
    TransactionTaskOut,
    TransactionUploadCallback,
    TransactionUploadFileOut,
    TransactionUploadInit,
    TransactionUploadInitOut,
)
from app.services.audit_service import AuditService
from app.services.oss_service import assume_sts_role, oss_service
from app.services.transaction_accounting_service import TransactionAccountingService
from app.utils.query_filters import parse_query_datetime
from app.models.transaction_accounting import TransactionTask, TransactionUploadFile

router = APIRouter()


class TransactionUploadInitResponse(BaseModel):
    file: TransactionUploadFileOut
    upload: TransactionUploadInitOut


class TransactionTaskBatchActionIn(BaseModel):
    task_ids: list[int]


class TransactionTaskBatchActionOut(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_ids: list[int]
    failed_items: list[dict[str, object]]


def _client_info(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _task_out(task, upload_file, org_name: str | None = None) -> TransactionTaskOut:
    item = TransactionTaskOut.model_validate(task)
    item.result_summary = _normalize_transaction_summary(item.result_summary)
    item.org_name = org_name
    item.original_name = upload_file.original_name
    item.shop_id = upload_file.shop_id
    item.platform_code = upload_file.platform_code
    item.shop_name = upload_file.shop_name
    item.accounting_year = upload_file.accounting_year
    item.accounting_month = upload_file.accounting_month
    return item


def _parse_ids(raw_ids: str | None) -> list[int]:
    if not raw_ids:
        return []
    ids: list[int] = []
    for raw in raw_ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            ids.append(int(raw))
        except ValueError as exc:
            raise ValueError("ids 参数格式错误") from exc
    return ids


def _month_filter_label(
    *,
    start_year: int | None = None,
    start_month: int | None = None,
    end_year: int | None = None,
    end_month: int | None = None,
    year: int | None = None,
    month: int | None = None,
) -> str | None:
    if start_year and start_month and end_year and end_month:
        start_label = f"{int(start_year)}年{int(start_month):02d}月"
        end_label = f"{int(end_year)}年{int(end_month):02d}月"
        return start_label if start_label == end_label else f"{start_label}-{end_label}"
    if start_year and start_month:
        return f"{int(start_year)}年{int(start_month):02d}月起"
    if end_year and end_month:
        return f"截至{int(end_year)}年{int(end_month):02d}月"
    if year and month:
        return f"{int(year)}年{int(month):02d}月"
    return None


def _export_response(buffer, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def _normalize_transaction_summary(result_summary: dict | None) -> dict | None:
    if not result_summary:
        return result_summary
    labels = {
        "total_rows": "总行数",
        "success_rows": "成功行数",
        "matched_rows": "匹配明细数",
        "unmatched_rows": "未匹配行数",
        "failed_rows": "失败行数",
        "summary_groups": "汇总分组数",
    }
    normalized: dict = {}
    for key, value in result_summary.items():
        normalized[labels.get(key, key)] = value
    return normalized


def _rule_display_name(rule) -> str:
    scene = getattr(rule, "transaction_scene", None)
    remark = getattr(rule, "remark_pattern", None)
    if scene == "":
        scene = "空场景"
    return remark or scene or getattr(rule, "transaction_direction", "") or str(getattr(rule, "id", ""))


@router.get("/major-categories", response_model=ApiResponse[list[TransactionMajorCategoryOut]])
async def list_major_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    items = await TransactionAccountingService.list_major_categories(db, user=current_user)
    return ApiResponse(data=[TransactionMajorCategoryOut.model_validate(item) for item in items])


@router.post("/major-categories", response_model=ApiResponse[TransactionMajorCategoryOut])
async def create_major_category(
    body: TransactionMajorCategoryCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        item = await TransactionAccountingService.create_major_category(db, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=None,
        module="transaction_accounting",
        action="config_change",
        description=f"新增资金大分类 [{item.name}]",
        target_type="transaction_major_category",
        target_id=item.id,
        target_name=item.name,
        ip=ip,
        user_agent=ua,
    )
    return ApiResponse(data=TransactionMajorCategoryOut.model_validate(item))


@router.put("/major-categories/{major_category_id}", response_model=ApiResponse[TransactionMajorCategoryOut])
async def update_major_category(
    major_category_id: int,
    body: TransactionMajorCategoryUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        item = await TransactionAccountingService.update_major_category(
            db,
            major_category_id=major_category_id,
            data=body,
            user=current_user,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    if item is None:
        return ApiResponse(code=404, message="大分类不存在")
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=None,
        module="transaction_accounting",
        action="config_change",
        description=f"修改资金大分类 [{item.name}]",
        target_type="transaction_major_category",
        target_id=item.id,
        target_name=item.name,
        ip=ip,
        user_agent=ua,
    )
    return ApiResponse(data=TransactionMajorCategoryOut.model_validate(item))


@router.delete("/major-categories/{major_category_id}", response_model=ApiResponse[None])
async def delete_major_category(
    major_category_id: int,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        ok = await TransactionAccountingService.delete_major_category(
            db,
            major_category_id=major_category_id,
            user=current_user,
        )
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if not ok:
        return ApiResponse(code=404, message="大分类不存在")
    return ApiResponse(message="已删除")


@router.get("/cash-flow-items", response_model=ApiResponse[list[TransactionCashFlowItemOut]])
async def list_cash_flow_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    items = await TransactionAccountingService.list_cash_flow_items(db, user=current_user)
    data = []
    for item in items:
        payload = TransactionCashFlowItemOut.model_validate(item)
        payload.parent_name = getattr(item, "parent_name", None)
        data.append(payload)
    return ApiResponse(data=data)


@router.get("/subjects", response_model=ApiResponse[list[TransactionSubjectOut]])
async def list_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    subjects = await TransactionAccountingService.list_subjects(db, user=current_user)
    return ApiResponse(data=[TransactionSubjectOut.model_validate(item) for item in subjects])


@router.post("/subjects", response_model=ApiResponse[TransactionSubjectOut])
async def create_subject(
    body: TransactionSubjectCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        subject = await TransactionAccountingService.create_subject(db, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=None,
        module="transaction_accounting",
        action="config_change",
        description=f"新增动账核算科目 [{subject.name}]",
        target_type="transaction_subject",
        target_id=subject.id,
        target_name=subject.name,
        ip=ip,
        user_agent=ua,
    )
    return ApiResponse(data=TransactionSubjectOut.model_validate(subject))


@router.put("/subjects/{subject_id}", response_model=ApiResponse[TransactionSubjectOut])
async def update_subject(
    subject_id: int,
    body: TransactionSubjectUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        subject = await TransactionAccountingService.update_subject(db, subject_id=subject_id, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if subject is None:
        return ApiResponse(code=404, message="科目不存在")
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=None,
        module="transaction_accounting",
        action="config_change",
        description=f"修改动账核算科目 [{subject.name}]",
        target_type="transaction_subject",
        target_id=subject.id,
        target_name=subject.name,
        ip=ip,
        user_agent=ua,
    )
    return ApiResponse(data=TransactionSubjectOut.model_validate(subject))


@router.delete("/subjects/{subject_id}", response_model=ApiResponse[None])
async def delete_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        ok = await TransactionAccountingService.delete_subject(db, subject_id=subject_id, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if not ok:
        return ApiResponse(code=404, message="科目不存在")
    return ApiResponse(message="已删除")


@router.get("/categories", response_model=ApiResponse[list[TransactionCategoryOut]])
async def list_categories(
    subject_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    categories = await TransactionAccountingService.list_categories(db, user=current_user, subject_id=subject_id)
    return ApiResponse(data=[TransactionCategoryOut.model_validate(item) for item in categories])


@router.post("/categories", response_model=ApiResponse[TransactionCategoryOut])
async def create_category(
    body: TransactionCategoryCreate,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        category = await TransactionAccountingService.create_category(db, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=TransactionCategoryOut.model_validate(category))


@router.put("/categories/{category_id}", response_model=ApiResponse[TransactionCategoryOut])
async def update_category(
    category_id: int,
    body: TransactionCategoryUpdate,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        category = await TransactionAccountingService.update_category(db, category_id=category_id, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    if category is None:
        return ApiResponse(code=404, message="重分类不存在")
    return ApiResponse(data=TransactionCategoryOut.model_validate(category))


@router.delete("/categories/{category_id}", response_model=ApiResponse[None])
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        ok = await TransactionAccountingService.delete_category(db, category_id=category_id, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if not ok:
        return ApiResponse(code=404, message="重分类不存在")
    return ApiResponse(message="已删除")


@router.get("/rules", response_model=ApiResponse[list[TransactionRuleOut]])
async def list_rules(
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    rows = await TransactionAccountingService.list_rules(db, user=current_user)
    data = []
    for rule, subject_name, category_name in rows:
        item = TransactionRuleOut.model_validate(rule)
        item.subject_name = subject_name
        item.category_name = category_name
        item.reclassification_name = category_name
        data.append(item)
    return ApiResponse(data=data)


@router.post("/rules", response_model=ApiResponse[TransactionRuleOut])
async def create_rule(
    body: TransactionRuleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        rule = await TransactionAccountingService.create_rule(db, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=None,
        module="transaction_accounting",
        action="config_change",
        description=f"新增动账核算规则 [{_rule_display_name(rule)}]",
        target_type="transaction_rule",
        target_id=rule.id,
        target_name=_rule_display_name(rule),
        ip=ip,
        user_agent=ua,
    )
    return ApiResponse(data=TransactionRuleOut.model_validate(rule))


@router.put("/rules/{rule_id}", response_model=ApiResponse[TransactionRuleOut])
async def update_rule(
    rule_id: int,
    body: TransactionRuleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        rule = await TransactionAccountingService.update_rule(db, rule_id=rule_id, data=body, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    if rule is None:
        return ApiResponse(code=404, message="规则不存在")
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=None,
        module="transaction_accounting",
        action="config_change",
        description=f"修改动账核算规则 [{_rule_display_name(rule)}]",
        target_type="transaction_rule",
        target_id=rule.id,
        target_name=_rule_display_name(rule),
        ip=ip,
        user_agent=ua,
    )
    return ApiResponse(data=TransactionRuleOut.model_validate(rule))


@router.delete("/rules/{rule_id}", response_model=ApiResponse[None])
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        ok = await TransactionAccountingService.delete_rule(db, rule_id=rule_id, user=current_user)
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if not ok:
        return ApiResponse(code=404, message="规则不存在")
    return ApiResponse(message="已删除")


@router.post("/upload-init", response_model=ApiResponse[TransactionUploadInitResponse])
async def upload_init(
    body: TransactionUploadInit,
    org_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not settings.ALIYUN_STS_ROLE_ARN or not settings.ALIYUN_ACCESS_KEY_ID:
        return ApiResponse(code=501, message="阿里云 OSS STS 未配置")
    try:
        upload_file = await TransactionAccountingService.init_upload(db, data=body, user=current_user, org_id=org_id)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    try:
        creds = assume_sts_role(
            role_arn=settings.ALIYUN_STS_ROLE_ARN,
            session_name=f"finengine-ta-{upload_file.org_id}-{upload_file.id}-{current_user.id}",
            duration_seconds=settings.ALIYUN_STS_EXPIRE_SECONDS,
        )
    except Exception:
        return ApiResponse(code=502, message="获取 OSS 上传凭证失败，请稍后重试")
    prefix = f"user-upload/transaction-accounting/{upload_file.org_id}/{upload_file.id}/"
    return ApiResponse(
        data=TransactionUploadInitResponse(
            file=TransactionUploadFileOut.model_validate(upload_file),
            upload=TransactionUploadInitOut(
                file_id=upload_file.id,
                access_key_id=creds["access_key_id"],
                access_key_secret=creds["access_key_secret"],
                security_token=creds["security_token"],
                expiration=creds["expiration"],
                region=settings.ALIYUN_OSS_REGION,
                bucket=settings.ALIYUN_OSS_BUCKET,
                endpoint=oss_service.normalized_endpoint(),
                oss_key_prefix=prefix,
            ),
        )
    )


@router.post("/upload-callback", response_model=ApiResponse[TransactionTaskOut])
async def upload_callback(
    body: TransactionUploadCallback,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        task = await TransactionAccountingService.upload_callback(db, data=body, user=current_user, ip=ip, user_agent=ua)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    upload_file = await db.get(TransactionUploadFile, task.file_id)
    return ApiResponse(data=_task_out(task, upload_file))


@router.get("/tasks", response_model=ApiResponse[PageResponse[TransactionTaskOut]])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    status: str | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    created_start_time: str | None = Query(None),
    created_end_time: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await TransactionAccountingService.list_tasks(
        db,
        user=current_user,
        org_id=org_id,
        status=status,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_ids=shop_ids,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        keyword=keyword,
        created_start_time=parse_query_datetime(created_start_time),
        created_end_time=parse_query_datetime(created_end_time),
        page=page,
        page_size=page_size,
    )
    items = [_task_out(task, upload_file, org_name) for task, upload_file, org_name in rows]
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.post("/tasks/{task_id}/run", response_model=ApiResponse[TransactionTaskOut])
async def rerun_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    ip, ua = _client_info(request)
    try:
        task = await TransactionAccountingService.rerun_task(db, task_id=task_id, user=current_user, ip=ip, user_agent=ua)
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if task is None:
        return ApiResponse(code=404, message="任务不存在")
    upload_file = await db.get(TransactionUploadFile, task.file_id)
    return ApiResponse(data=_task_out(task, upload_file))


@router.post("/tasks/batch/recalculate", response_model=ApiResponse[TransactionTaskBatchActionOut])
async def batch_recalculate_tasks(
    body: TransactionTaskBatchActionIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    task_ids = list(dict.fromkeys(body.task_ids))
    if not task_ids:
        return ApiResponse(code=400, message="请选择任务")
    if len(task_ids) > 100:
        return ApiResponse(code=400, message="单次最多操作 100 个任务")

    ip, ua = _client_info(request)
    success_ids: list[int] = []
    failed_items: list[dict[str, object]] = []
    for task_id in task_ids:
        task = await db.get(TransactionTask, task_id)
        if task is None or task.is_deleted:
            failed_items.append({"task_id": task_id, "message": "任务不存在"})
            continue
        if current_user.role != "superadmin" and task.org_id != current_user.org_id:
            failed_items.append({"task_id": task_id, "message": "数据不存在或无权访问"})
            continue
        if task.status in {"queued", "processing"}:
            failed_items.append({"task_id": task_id, "message": "排队中或运行中的任务不能重新统计"})
            continue

        try:
            rerun = await TransactionAccountingService.rerun_task(db, task_id=task_id, user=current_user, ip=ip, user_agent=ua)
        except ValueError as exc:
            failed_items.append({"task_id": task_id, "message": str(exc)})
            continue
        if rerun is None:
            failed_items.append({"task_id": task_id, "message": "任务不存在"})
            continue
        success_ids.append(rerun.id)

    data = TransactionTaskBatchActionOut(
        total=len(task_ids),
        success_count=len(success_ids),
        failed_count=len(failed_items),
        success_ids=success_ids,
        failed_items=failed_items,
    )
    message = "操作完成" if not failed_items else f"成功 {data.success_count} 个，失败 {data.failed_count} 个"
    return ApiResponse(data=data, message=message)


@router.get("/details", response_model=ApiResponse[PageResponse[TransactionDetailOut]])
async def list_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org_id: str | None = Query(None),
    task_id: int | None = Query(None),
    status: str | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    major_category_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    category_id: str | None = Query(None),
    transaction_direction: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    upload_accounting_year: int | None = Query(None),
    upload_accounting_month: int | None = Query(None),
    upload_accounting_start_year: int | None = Query(None),
    upload_accounting_start_month: int | None = Query(None),
    upload_accounting_end_year: int | None = Query(None),
    upload_accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await TransactionAccountingService.list_details(
        db,
        user=current_user,
        org_id=org_id,
        task_id=task_id,
        status=status,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_ids=shop_ids,
        major_category_id=major_category_id,
        subject_id=subject_id,
        category_id=category_id,
        transaction_direction=transaction_direction,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        upload_accounting_year=upload_accounting_year,
        upload_accounting_month=upload_accounting_month,
        upload_accounting_start_year=upload_accounting_start_year,
        upload_accounting_start_month=upload_accounting_start_month,
        upload_accounting_end_year=upload_accounting_end_year,
        upload_accounting_end_month=upload_accounting_end_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = []
    for detail in rows:
        item = TransactionDetailOut.model_validate(detail)
        item.reclassification_name = item.category_name
        items.append(item)
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/details/export")
async def export_details(
    request: Request,
    org_id: str | None = Query(None),
    task_id: int | None = Query(None),
    status: str | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    major_category_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    category_id: str | None = Query(None),
    transaction_direction: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    upload_accounting_year: int | None = Query(None),
    upload_accounting_month: int | None = Query(None),
    upload_accounting_start_year: int | None = Query(None),
    upload_accounting_start_month: int | None = Query(None),
    upload_accounting_end_year: int | None = Query(None),
    upload_accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    scope: str = Query("all", pattern="^(all|current_page|selected)$"),
    ids: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        selected_ids = _parse_ids(ids) if scope == "selected" else None
        buffer = await TransactionAccountingService.export_details(
            db,
            user=current_user,
            org_id=org_id,
            task_id=task_id,
            status=status,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            major_category_id=major_category_id,
            subject_id=subject_id,
            category_id=category_id,
            transaction_direction=transaction_direction,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            upload_accounting_year=upload_accounting_year,
            upload_accounting_month=upload_accounting_month,
            upload_accounting_start_year=upload_accounting_start_year,
            upload_accounting_start_month=upload_accounting_start_month,
            upload_accounting_end_year=upload_accounting_end_year,
            upload_accounting_end_month=upload_accounting_end_month,
            keyword=keyword,
            ids=selected_ids,
            page=page if scope == "current_page" else None,
            page_size=page_size if scope == "current_page" else None,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))

    ip, ua = _client_info(request)
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="transaction_accounting",
        action="export",
        description="导出动账汇总明细",
        ip=ip,
        user_agent=ua,
        extra_data={"scope": scope, "ids": selected_ids, "task_id": task_id, "status": status},
    )

    parts = ["动账汇总明细"]
    month_label = _month_filter_label(
        start_year=accounting_start_year,
        start_month=accounting_start_month,
        end_year=accounting_end_year,
        end_month=accounting_end_month,
        year=accounting_year,
        month=accounting_month,
    )
    if month_label:
        parts.append(month_label)
    if shop_name:
        parts.append(shop_name)
    if scope == "current_page":
        parts.append(f"第{page}页")
    if scope == "selected":
        parts.append("选中")
    return _export_response(buffer, "_".join(parts) + ".xlsx")


@router.get("/summary", response_model=ApiResponse[PageResponse[TransactionSummaryOut]])
async def list_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org_id: str | None = Query(None),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    major_category_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    category_id: str | None = Query(None),
    transaction_direction: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    upload_accounting_year: int | None = Query(None),
    upload_accounting_month: int | None = Query(None),
    upload_accounting_start_year: int | None = Query(None),
    upload_accounting_start_month: int | None = Query(None),
    upload_accounting_end_year: int | None = Query(None),
    upload_accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await TransactionAccountingService.list_summaries(
        db,
        user=current_user,
        org_id=org_id,
        task_id=task_id,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_ids=shop_ids,
        major_category_id=major_category_id,
        subject_id=subject_id,
        category_id=category_id,
        transaction_direction=transaction_direction,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        upload_accounting_year=upload_accounting_year,
        upload_accounting_month=upload_accounting_month,
        upload_accounting_start_year=upload_accounting_start_year,
        upload_accounting_start_month=upload_accounting_start_month,
        upload_accounting_end_year=upload_accounting_end_year,
        upload_accounting_end_month=upload_accounting_end_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = []
    for row in rows:
        item = TransactionSummaryOut.model_validate(row)
        item.reclassification_name = item.category_name
        items.append(item)
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/summary/annual", response_model=ApiResponse[TransactionAnnualSummaryOut])
async def get_annual_summary(
    year: int = Query(..., ge=2000, le=2100),
    org_id: str | None = Query(None),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    major_category_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    category_id: str | None = Query(None),
    transaction_direction: str | None = Query(None),
    upload_accounting_year: int | None = Query(None),
    upload_accounting_month: int | None = Query(None),
    upload_accounting_start_year: int | None = Query(None),
    upload_accounting_start_month: int | None = Query(None),
    upload_accounting_end_year: int | None = Query(None),
    upload_accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        report = await TransactionAccountingService.get_annual_summary(
            db,
            user=current_user,
            year=year,
            org_id=org_id,
            task_id=task_id,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            major_category_id=major_category_id,
            subject_id=subject_id,
            category_id=category_id,
            transaction_direction=transaction_direction,
            upload_accounting_year=upload_accounting_year,
            upload_accounting_month=upload_accounting_month,
            upload_accounting_start_year=upload_accounting_start_year,
            upload_accounting_start_month=upload_accounting_start_month,
            upload_accounting_end_year=upload_accounting_end_year,
            upload_accounting_end_month=upload_accounting_end_month,
            keyword=keyword,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=TransactionAnnualSummaryOut.model_validate(report))


@router.get("/summary/annual/export")
async def export_annual_summary(
    request: Request,
    year: int = Query(..., ge=2000, le=2100),
    org_id: str | None = Query(None),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    major_category_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    category_id: str | None = Query(None),
    transaction_direction: str | None = Query(None),
    upload_accounting_year: int | None = Query(None),
    upload_accounting_month: int | None = Query(None),
    upload_accounting_start_year: int | None = Query(None),
    upload_accounting_start_month: int | None = Query(None),
    upload_accounting_end_year: int | None = Query(None),
    upload_accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        buffer = await TransactionAccountingService.export_annual_summary(
            db,
            user=current_user,
            year=year,
            org_id=org_id,
            task_id=task_id,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            major_category_id=major_category_id,
            subject_id=subject_id,
            category_id=category_id,
            transaction_direction=transaction_direction,
            upload_accounting_year=upload_accounting_year,
            upload_accounting_month=upload_accounting_month,
            upload_accounting_start_year=upload_accounting_start_year,
            upload_accounting_start_month=upload_accounting_start_month,
            upload_accounting_end_year=upload_accounting_end_year,
            upload_accounting_end_month=upload_accounting_end_month,
            keyword=keyword,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))

    ip, ua = _client_info(request)
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="transaction_accounting",
        action="export",
        description=f"导出{year}年年度报表",
        ip=ip,
        user_agent=ua,
        extra_data={"year": year, "task_id": task_id},
    )

    parts = [f"{year}年年度报表"]
    if shop_name:
        parts.append(shop_name)
    return _export_response(buffer, "_".join(parts) + ".xlsx")


@router.get("/summary/export")
async def export_summaries(
    request: Request,
    org_id: str | None = Query(None),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    major_category_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    category_id: str | None = Query(None),
    transaction_direction: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    upload_accounting_year: int | None = Query(None),
    upload_accounting_month: int | None = Query(None),
    upload_accounting_start_year: int | None = Query(None),
    upload_accounting_start_month: int | None = Query(None),
    upload_accounting_end_year: int | None = Query(None),
    upload_accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    scope: str = Query("all", pattern="^(all|current_page|selected)$"),
    ids: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        selected_ids = _parse_ids(ids) if scope == "selected" else None
        buffer = await TransactionAccountingService.export_summaries(
            db,
            user=current_user,
            org_id=org_id,
            task_id=task_id,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            major_category_id=major_category_id,
            subject_id=subject_id,
            category_id=category_id,
            transaction_direction=transaction_direction,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            upload_accounting_year=upload_accounting_year,
            upload_accounting_month=upload_accounting_month,
            upload_accounting_start_year=upload_accounting_start_year,
            upload_accounting_start_month=upload_accounting_start_month,
            upload_accounting_end_year=upload_accounting_end_year,
            upload_accounting_end_month=upload_accounting_end_month,
            keyword=keyword,
            ids=selected_ids,
            page=page if scope == "current_page" else None,
            page_size=page_size if scope == "current_page" else None,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))

    ip, ua = _client_info(request)
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="transaction_accounting",
        action="export",
        description="导出动账汇总报表",
        ip=ip,
        user_agent=ua,
        extra_data={"scope": scope, "ids": selected_ids, "task_id": task_id},
    )

    parts = ["动账汇总报表"]
    month_label = _month_filter_label(
        start_year=accounting_start_year,
        start_month=accounting_start_month,
        end_year=accounting_end_year,
        end_month=accounting_end_month,
        year=accounting_year,
        month=accounting_month,
    )
    if month_label:
        parts.append(month_label)
    if shop_name:
        parts.append(shop_name)
    if scope == "current_page":
        parts.append(f"第{page}页")
    if scope == "selected":
        parts.append("选中")
    return _export_response(buffer, "_".join(parts) + ".xlsx")
