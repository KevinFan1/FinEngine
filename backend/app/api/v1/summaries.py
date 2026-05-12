"""Summaries API — query and export financial summaries."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.summary import SummaryOut, SummaryReportOut
from app.services.audit_service import AuditService
from app.services.summary_service import SummaryService

router = APIRouter()


def resolve_accounting_date_filters(
    *,
    accounting_year: int | None = None,
    accounting_month: int | None = None,
    source_year: int | None = None,
    source_month: int | None = None,
) -> tuple[int | None, int | None]:
    return (
        accounting_year if accounting_year is not None else source_year,
        accounting_month if accounting_month is not None else source_month,
    )


def resolve_accounting_date_range_filters(
    *,
    accounting_start_year: int | None = None,
    accounting_start_month: int | None = None,
    accounting_end_year: int | None = None,
    accounting_end_month: int | None = None,
) -> tuple[int | None, int | None, int | None, int | None]:
    return accounting_start_year, accounting_start_month, accounting_end_year, accounting_end_month


def month_filter_label(
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
    if year:
        return f"{int(year)}年"
    if month:
        return f"{int(month):02d}月"
    return None


@router.get("", response_model=ApiResponse[PageResponse[SummaryOut]])
async def list_summaries(
    request: Request,
    summary_year: int | None = Query(None),
    summary_month: int | None = Query(None),
    source_year: int | None = Query(None),
    source_month: int | None = Query(None),
    platform_name: str | None = Query(None),
    report_platform_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    shop_name: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Query financial summaries with filters."""
    org_id = current_user.org_id if current_user.role != "superadmin" else current_user.org_id or 0

    summaries, total = await SummaryService.list_summaries(
        db,
        org_id=org_id,
        summary_year=summary_year,
        summary_month=summary_month,
        source_year=source_year,
        source_month=source_month,
        platform_name=platform_name,
        report_platform_name=report_platform_name,
        shop_id=shop_id,
        shop_name=shop_name,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    # await AuditService.log(
    #     db,
    #     user_id=current_user.id,
    #     username=current_user.username,
    #     display_name=current_user.display_name,
    #     org_id=current_user.org_id,
    #     module="summary",
    #     action="view",
    #     description=f"用户 [{current_user.display_name}] 查看汇总报表",
    #     ip=ip,
    #     user_agent=ua,
    #     extra_data={"year": summary_year, "month": summary_month},
    # )

    return ApiResponse(
        data=PageResponse(
            items=[to_summary_out(s) for s in summaries],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


def to_summary_out(summary) -> SummaryOut:
    """Map database summary fields to API/frontend field names."""
    shop_color = None
    if isinstance(summary, dict):
        shop_color = summary.get("shop_color")
        summary = summary.get("summary")
    source_platform_code = getattr(summary, "source_platform_code", None) or summary.platform_name
    report_platform_code = getattr(summary, "report_platform_code", None) or source_platform_code
    return SummaryOut(
        id=summary.id,
        org_id=summary.org_id,
        shop_id=summary.shop_id,
        summary_year=summary.summary_year,
        summary_month=summary.summary_month,
        summary_date=f"{summary.summary_year}-{summary.summary_month:02d}",
        source_year=summary.source_year,
        source_month=summary.source_month,
        source_date=month_date_label(summary.source_year, summary.source_month),
        platform_name=source_platform_code,
        source_platform_code=source_platform_code,
        report_platform_code=report_platform_code,
        shop_name=summary.shop_name,
        shop_color=shop_color or getattr(summary, "shop_color", None),
        year=summary.summary_year,
        month=summary.summary_month,
        platform=source_platform_code,
        source_platform=source_platform_code,
        report_platform=report_platform_code,
        gmv=float(summary.gmv or 0),
        real_gmv=float(summary.gmv or 0),
        platform_income=float(summary.platform_income or 0),
        platform_other_income=float(summary.platform_income or 0),
        platform_fee=float(summary.platform_fee or 0),
        platform_service_fee=float(summary.platform_fee or 0),
        return_cost=float(summary.return_cost or 0),
        return_and_other_fee=float(summary.return_cost or 0),
        commission=float(summary.commission or 0),
        daren_commission=float(summary.commission or 0),
        merchant_fee=float(summary.merchant_fee or 0),
        zhaoshang_service_fee=float(summary.merchant_fee or 0),
        promotion_fee=float(summary.promotion_fee or 0),
        outside_promotion_fee=float(summary.promotion_fee or 0),
        provider_commission=float(summary.provider_commission or 0),
        service_provider_commission=float(summary.provider_commission or 0),
        donation_fee=float(summary.donation_fee or 0),
        payment_donation_fee=float(summary.donation_fee or 0),
        insurance_fee=float(summary.insurance_fee or 0),
        shipping_insurance=float(summary.insurance_fee or 0),
        bic=float(summary.bic or 0),
        extra_data=summary.extra_data,
        source_file_ids=summary.source_file_ids or [],
        last_file_id=summary.last_file_id,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


@router.get("/report", response_model=ApiResponse[PageResponse[SummaryReportOut]])
async def list_report_summaries(
    request: Request,
    accounting_start_year: int | None = Query(None, description="核算开始年份"),
    accounting_start_month: int | None = Query(None, description="核算开始月份"),
    accounting_end_year: int | None = Query(None, description="核算结束年份"),
    accounting_end_month: int | None = Query(None, description="核算结束月份"),
    accounting_year: int | None = Query(None, description="核算年份"),
    accounting_month: int | None = Query(None, description="核算月份"),
    source_year: int | None = Query(None),
    source_month: int | None = Query(None),
    platform_name: str | None = Query(None),
    report_platform_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    shop_name: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Query accounting-month aggregated financial reports."""
    org_id = current_user.org_id if current_user.role != "superadmin" else current_user.org_id or 0
    filter_year, filter_month = resolve_accounting_date_filters(
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        source_year=source_year,
        source_month=source_month,
    )
    range_start_year, range_start_month, range_end_year, range_end_month = resolve_accounting_date_range_filters(
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
    )

    rows, total = await SummaryService.list_report_summaries(
        db,
        org_id=org_id,
        source_year=filter_year,
        source_month=filter_month,
        source_start_year=range_start_year,
        source_start_month=range_start_month,
        source_end_year=range_end_year,
        source_end_month=range_end_month,
        platform_name=platform_name,
        report_platform_name=report_platform_name,
        shop_id=shop_id,
        shop_name=shop_name,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=PageResponse(
            items=[to_summary_report_out(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


def to_summary_report_out(row: dict) -> SummaryReportOut:
    source_year = int(row.get("source_year") or 0)
    source_month = int(row.get("source_month") or 0)
    platform_name = str(row.get("platform_name") or "")
    report_platform_code = str(row.get("report_platform_code") or platform_name)
    shop_id = int(row.get("shop_id") or 0)
    shop_name = str(row.get("shop_name") or "")
    record_id = f"{source_year}-{source_month}-{platform_name}-{shop_id}"
    return SummaryReportOut(
        id=record_id,
        org_id=int(row.get("org_id") or 0),
        shop_id=shop_id,
        source_year=source_year,
        source_month=source_month,
        source_date=month_date_label(source_year, source_month),
        platform_name=platform_name,
        report_platform_code=report_platform_code,
        shop_name=shop_name,
        shop_color=row.get("shop_color"),
        year=source_year,
        month=source_month,
        platform=platform_name,
        report_platform=report_platform_code,
        summary_count=int(row.get("summary_count") or 0),
        original_gmv=float(row.get("original_gmv") or row.get("gmv") or 0),
        gmv_adjustment=float(row.get("gmv_adjustment") or 0),
        gmv=float(row.get("gmv") or 0),
        real_gmv=float(row.get("gmv") or 0),
        platform_income=float(row.get("platform_income") or 0),
        platform_other_income=float(row.get("platform_income") or 0),
        platform_fee=float(row.get("platform_fee") or 0),
        platform_service_fee=float(row.get("platform_fee") or 0),
        original_return_cost=float(row.get("original_return_cost") or row.get("return_cost") or 0),
        return_cost_adjustment=float(row.get("return_cost_adjustment") or 0),
        return_cost=float(row.get("return_cost") or 0),
        return_and_other_fee=float(row.get("return_cost") or 0),
        commission=float(row.get("commission") or 0),
        daren_commission=float(row.get("commission") or 0),
        merchant_fee=float(row.get("merchant_fee") or 0),
        zhaoshang_service_fee=float(row.get("merchant_fee") or 0),
        promotion_fee=float(row.get("promotion_fee") or 0),
        outside_promotion_fee=float(row.get("promotion_fee") or 0),
        provider_commission=float(row.get("provider_commission") or 0),
        service_provider_commission=float(row.get("provider_commission") or 0),
        donation_fee=float(row.get("donation_fee") or 0),
        payment_donation_fee=float(row.get("donation_fee") or 0),
        insurance_fee=float(row.get("insurance_fee") or 0),
        shipping_insurance=float(row.get("insurance_fee") or 0),
        bic=float(row.get("bic") or 0),
    )


def month_date_label(year: int | None, month: int | None) -> str:
    if not year or not month:
        return "未解析"
    return f"{int(year)}-{int(month):02d}"


@router.get("/report/export")
async def export_report_summaries(
    request: Request,
    accounting_start_year: int | None = Query(None, description="核算开始年份"),
    accounting_start_month: int | None = Query(None, description="核算开始月份"),
    accounting_end_year: int | None = Query(None, description="核算结束年份"),
    accounting_end_month: int | None = Query(None, description="核算结束月份"),
    accounting_year: int | None = Query(None, description="核算年份"),
    accounting_month: int | None = Query(None, description="核算月份"),
    source_year: int | None = Query(None),
    source_month: int | None = Query(None),
    platform_name: str | None = Query(None),
    report_platform_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    shop_name: str | None = Query(None),
    keyword: str | None = Query(None),
    scope: str = Query("all", pattern="^(all|current_page|selected)$"),
    ids: str | None = Query(None, description="Comma-separated report row IDs for selected export"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Export accounting-month aggregated reports to Excel."""
    org_id = current_user.org_id if current_user.role != "superadmin" else current_user.org_id or 0
    selected_ids = parse_report_ids(ids) if scope == "selected" else None
    filter_year, filter_month = resolve_accounting_date_filters(
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        source_year=source_year,
        source_month=source_month,
    )
    range_start_year, range_start_month, range_end_year, range_end_month = resolve_accounting_date_range_filters(
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
    )
    buffer = await SummaryService.export_report_summaries(
        db,
        org_id=org_id,
        source_year=filter_year,
        source_month=filter_month,
        source_start_year=range_start_year,
        source_start_month=range_start_month,
        source_end_year=range_end_year,
        source_end_month=range_end_month,
        platform_name=platform_name,
        report_platform_name=report_platform_name,
        shop_id=shop_id,
        shop_name=shop_name,
        keyword=keyword,
        ids=selected_ids,
        page=page if scope == "current_page" else None,
        page_size=page_size if scope == "current_page" else None,
    )

    parts = ["汇总报表"]
    date_label = month_filter_label(
        start_year=range_start_year,
        start_month=range_start_month,
        end_year=range_end_year,
        end_month=range_end_month,
        year=filter_year,
        month=filter_month,
    )
    if date_label:
        parts.append(date_label)
    if platform_name:
        parts.append(platform_name)
    if shop_name:
        parts.append(shop_name)
    elif shop_id is not None:
        parts.append(f"店铺{shop_id}")
    if scope == "current_page":
        parts.append(f"第{page}页")
    if scope == "selected":
        parts.append("选中")
    filename = "_".join(parts) + ".xlsx"
    safe_filename = quote(filename)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="summary",
        action="export",
        description=f"用户 [{current_user.display_name}] 导出汇总报表",
        ip=ip,
        user_agent=ua,
        extra_data={
            "accounting_year": filter_year,
            "accounting_month": filter_month,
            "accounting_start_year": range_start_year,
            "accounting_start_month": range_start_month,
            "accounting_end_year": range_end_year,
            "accounting_end_month": range_end_month,
            "platform": platform_name,
            "shop_id": shop_id,
            "shop": shop_name,
            "keyword": keyword,
            "scope": scope,
            "ids": selected_ids,
            "page": page if scope == "current_page" else None,
            "page_size": page_size if scope == "current_page" else None,
        },
    )

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
    )


@router.get("/export")
async def export_summaries(
    request: Request,
    summary_year: int | None = Query(None),
    summary_month: int | None = Query(None),
    source_year: int | None = Query(None),
    source_month: int | None = Query(None),
    platform_name: str | None = Query(None),
    report_platform_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    shop_name: str | None = Query(None),
    keyword: str | None = Query(None),
    scope: str = Query("all", pattern="^(all|current_page|selected)$"),
    ids: str | None = Query(None, description="Comma-separated summary IDs for selected export"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Export summaries to Excel. Returns a streaming .xlsx file."""
    org_id = current_user.org_id if current_user.role != "superadmin" else current_user.org_id or 0
    selected_ids = parse_summary_ids(ids) if scope == "selected" else None

    buffer = await SummaryService.export_summaries(
        db,
        org_id=org_id,
        summary_year=summary_year,
        summary_month=summary_month,
        source_year=source_year,
        source_month=source_month,
        platform_name=platform_name,
        report_platform_name=report_platform_name,
        shop_id=shop_id,
        shop_name=shop_name,
        keyword=keyword,
        ids=selected_ids,
        page=page if scope == "current_page" else None,
        page_size=page_size if scope == "current_page" else None,
    )

    # Build filename
    parts = ["财务汇总"]
    if summary_year:
        parts.append(f"{summary_year}年")
    if summary_month:
        parts.append(f"{summary_month}月")
    if source_year or source_month:
        parts.append(f"上传{source_year or '全部'}年{source_month or '全部'}月")
    if platform_name:
        parts.append(platform_name)
    if shop_name:
        parts.append(shop_name)
    elif shop_id is not None:
        parts.append(f"店铺{shop_id}")
    if scope == "current_page":
        parts.append(f"第{page}页")
    if scope == "selected":
        parts.append("选中")
    filename = "_".join(parts) + ".xlsx"
    safe_filename = quote(filename)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="summary",
        action="export",
        description=f"用户 [{current_user.display_name}] 导出汇总报表",
        ip=ip,
        user_agent=ua,
        extra_data={
            "year": summary_year,
            "month": summary_month,
            "source_year": source_year,
            "source_month": source_month,
            "platform": platform_name,
            "report_platform": report_platform_name,
            "shop_id": shop_id,
            "shop": shop_name,
            "keyword": keyword,
            "scope": scope,
            "ids": selected_ids,
            "page": page if scope == "current_page" else None,
            "page_size": page_size if scope == "current_page" else None,
        },
    )

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
    )


def parse_summary_ids(raw_ids: str | None) -> list[int]:
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


def parse_report_ids(raw_ids: str | None) -> list[str]:
    if not raw_ids:
        return []
    return [raw.strip() for raw in raw_ids.split(",") if raw.strip()]
