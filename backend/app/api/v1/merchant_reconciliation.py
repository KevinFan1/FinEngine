"""Merchant reconciliation API."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.merchant_reconciliation import (
    MerchantBankFlowFileOut,
    MerchantBankFlowImportResult,
    MerchantBankFlowRowOut,
    MerchantOpeningBalanceBatchResult,
    MerchantOpeningBalanceBatchUpsert,
    MerchantOpeningBalanceOut,
    MerchantReconciliationDetailOut,
    MerchantReconciliationDetailPageOut,
    MerchantReconciliationSummaryOut,
    MerchantReconciliationSummaryPageOut,
    MerchantRedSheetImportResult,
    MerchantRedSheetOut,
    MerchantRedSheetPaymentOut,
    MerchantRedSheetPurchaseOut,
)
from app.services.merchant_reconciliation_service import MerchantReconciliationService

router = APIRouter()


def _export_response(buffer, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def _parse_ids(raw_ids: str | None) -> list[int] | None:
    if raw_ids is None:
        return None
    ids: list[int] = []
    for raw in raw_ids.split(","):
        raw = raw.strip()
        if raw:
            ids.append(int(raw))
    return ids


def _parse_str_ids(raw_ids: str | None) -> list[str] | None:
    if raw_ids is None:
        return None
    return [raw.strip() for raw in raw_ids.split(",") if raw.strip()]


@router.get("/red-sheet-template")
async def download_red_sheet_template(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    buffer = MerchantReconciliationService.build_red_sheet_template(
        accounting_year=accounting_year,
        accounting_month=accounting_month,
    )
    return _export_response(buffer, f"{accounting_year}{accounting_month:02d}红单导入模板.xlsx")


@router.post("/red-sheets/import", response_model=ApiResponse[MerchantRedSheetImportResult])
async def import_red_sheet(
    request: Request,
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    org_id: str | None = Query(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    content = await file.read()
    try:
        result = await MerchantReconciliationService.import_red_sheet(
            db,
            content=content,
            filename=file.filename or "",
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            org_id=org_id,
            operator=current_user,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=result, message="导入完成")


@router.post("/bank-flows/import", response_model=ApiResponse[MerchantBankFlowImportResult])
async def import_bank_flow(
    request: Request,
    org_id: str | None = Query(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    import tempfile
    from pathlib import Path

    suffix = Path(file.filename or "").suffix or ".xls"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            tmp.write(chunk)
        tmp.flush()
        try:
            result = await MerchantReconciliationService.import_bank_flow(
                db,
                file_path=tmp.name,
                filename=file.filename or "",
                org_id=org_id,
                operator=current_user,
                file_size=size,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        except ValueError as exc:
            return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=result, message="导入完成")


@router.get("/red-sheets", response_model=ApiResponse[PageResponse[MerchantRedSheetOut]])
async def list_red_sheets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    shop_ids: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_red_sheets(
        db,
        user=current_user,
        org_id=org_id,
        shop_ids=shop_ids,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = [
        MerchantRedSheetOut.model_validate(red_sheet).model_copy(
            update={"org_name": org_name, "shop_color": shop_color}
        )
        for red_sheet, org_name, shop_color in rows
    ]
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/payments", response_model=ApiResponse[PageResponse[MerchantRedSheetPaymentOut]])
async def list_payment_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    shop_ids: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_payment_details(
        db,
        user=current_user,
        org_id=org_id,
        shop_ids=shop_ids,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantRedSheetPaymentOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/purchases", response_model=ApiResponse[PageResponse[MerchantRedSheetPurchaseOut]])
async def list_purchase_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    shop_ids: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_purchase_details(
        db,
        user=current_user,
        org_id=org_id,
        shop_ids=shop_ids,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantRedSheetPurchaseOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/bank-flow-files", response_model=ApiResponse[PageResponse[MerchantBankFlowFileOut]])
async def list_bank_flow_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_bank_flow_files(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = [
        MerchantBankFlowFileOut.model_validate(bank_flow_file).model_copy(update={"org_name": org_name})
        for bank_flow_file, org_name in rows
    ]
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/bank-flow-rows", response_model=ApiResponse[PageResponse[MerchantBankFlowRowOut]])
async def list_bank_flow_rows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_bank_flow_rows(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantBankFlowRowOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/details", response_model=ApiResponse[MerchantReconciliationDetailPageOut])
async def list_details(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    shop_id: int = Query(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    keyword: str | None = Query(None),
    match_status: str | None = Query(None),
    ids: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total, stats = await MerchantReconciliationService.list_details(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        shop_id=shop_id,
        org_id=org_id,
        keyword=keyword,
        match_status=match_status,
        ids=_parse_ids(ids),
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=MerchantReconciliationDetailPageOut(
            items=[MerchantReconciliationDetailOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            stats=stats,
        )
    )


@router.get("/details/export")
async def export_details(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    shop_id: int = Query(..., ge=1),
    org_id: str | None = Query(None),
    keyword: str | None = Query(None),
    match_status: str | None = Query(None),
    scope: str = Query("all"),
    ids: str | None = Query(None),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    selected_ids = _parse_ids(ids) if scope == "selected" else None
    export_page = page if scope == "current_page" else None
    export_page_size = page_size if scope == "current_page" else None
    buffer = await MerchantReconciliationService.export_details(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        shop_id=shop_id,
        org_id=org_id,
        keyword=keyword,
        match_status=match_status,
        ids=selected_ids,
        page=export_page,
        page_size=export_page_size,
    )
    filename = f"{accounting_year}{accounting_month:02d}_商家对账明细.xlsx"
    return _export_response(buffer, filename)


@router.get("/summary/opening-balances", response_model=ApiResponse[list[MerchantOpeningBalanceOut]])
async def list_summary_opening_balances(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    shop_id: int | None = Query(None, ge=1),
    org_id: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows = await MerchantReconciliationService.list_opening_balances_for_summary(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        shop_id=shop_id,
        org_id=org_id,
        keyword=keyword,
    )
    return ApiResponse(data=[MerchantOpeningBalanceOut(**row) for row in rows])


@router.post("/summary/opening-balances", response_model=ApiResponse[MerchantOpeningBalanceBatchResult])
async def upsert_summary_opening_balances(
    body: MerchantOpeningBalanceBatchUpsert,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        result = await MerchantReconciliationService.upsert_opening_balances(
            db,
            data=body,
            operator=current_user,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=result, message="保存完成")


@router.get("/summary", response_model=ApiResponse[MerchantReconciliationSummaryPageOut])
async def list_summary(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    shop_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    keyword: str | None = Query(None),
    bank_status: str | None = Query(None, pattern="^(pending|matched|diff)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_summary(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        shop_id=shop_id,
        org_id=org_id,
        keyword=keyword,
        bank_status=bank_status,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=MerchantReconciliationSummaryPageOut(
            items=[MerchantReconciliationSummaryOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/summary/details", response_model=ApiResponse[PageResponse[MerchantReconciliationDetailOut]])
async def list_summary_drilldown_details(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    our_subject: str = Query(..., min_length=1),
    merchant_receipt_subject: str = Query(..., min_length=1),
    summary_org_id: int | None = Query(None, ge=1),
    shop_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_summary_drilldown_details(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        summary_org_id=summary_org_id,
        our_subject=our_subject,
        merchant_receipt_subject=merchant_receipt_subject,
        shop_id=shop_id,
        org_id=org_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantReconciliationDetailOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/summary/payments", response_model=ApiResponse[PageResponse[MerchantRedSheetPaymentOut]])
async def list_summary_drilldown_payments(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    our_subject: str = Query(..., min_length=1),
    merchant_receipt_subject: str = Query(..., min_length=1),
    summary_org_id: int | None = Query(None, ge=1),
    shop_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_summary_drilldown_payments(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        summary_org_id=summary_org_id,
        our_subject=our_subject,
        merchant_receipt_subject=merchant_receipt_subject,
        shop_id=shop_id,
        org_id=org_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantRedSheetPaymentOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/summary/purchases", response_model=ApiResponse[PageResponse[MerchantRedSheetPurchaseOut]])
async def list_summary_drilldown_purchases(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    our_subject: str = Query(..., min_length=1),
    merchant_receipt_subject: str = Query(..., min_length=1),
    summary_org_id: int | None = Query(None, ge=1),
    shop_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_summary_drilldown_purchases(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        summary_org_id=summary_org_id,
        our_subject=our_subject,
        merchant_receipt_subject=merchant_receipt_subject,
        shop_id=shop_id,
        org_id=org_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantRedSheetPurchaseOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/summary/bank-flow-rows", response_model=ApiResponse[PageResponse[MerchantBankFlowRowOut]])
async def list_summary_drilldown_bank_flow_rows(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    our_subject: str = Query(..., min_length=1),
    merchant_receipt_subject: str = Query(..., min_length=1),
    summary_org_id: int | None = Query(None, ge=1),
    shop_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await MerchantReconciliationService.list_summary_drilldown_bank_flow_rows(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        summary_org_id=summary_org_id,
        our_subject=our_subject,
        merchant_receipt_subject=merchant_receipt_subject,
        shop_id=shop_id,
        org_id=org_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[MerchantBankFlowRowOut(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/summary/export")
async def export_summary(
    accounting_year: int = Query(..., ge=2000, le=2100),
    accounting_month: int = Query(..., ge=1, le=12),
    shop_id: int | None = Query(None, ge=1),
    org_id: str | None = Query(None),
    keyword: str | None = Query(None),
    bank_status: str | None = Query(None, pattern="^(pending|matched|diff)$"),
    scope: str = Query("all"),
    ids: str | None = Query(None),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    selected_ids = _parse_str_ids(ids) if scope == "selected" else None
    export_page = page if scope == "current_page" else None
    export_page_size = page_size if scope == "current_page" else None
    buffer = await MerchantReconciliationService.export_summary(
        db,
        user=current_user,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        shop_id=shop_id,
        org_id=org_id,
        keyword=keyword,
        bank_status=bank_status,
        ids=selected_ids,
        page=export_page,
        page_size=export_page_size,
    )
    filename = f"{accounting_year}{accounting_month:02d}_商家对账汇总.xlsx"
    return _export_response(buffer, filename)
