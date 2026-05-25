from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog


BRACKET_VALUE_RE = re.compile(r"\[([^\]]+)\]")
CATEGORY_DICT_STATS_RE = re.compile(r"(\d+)\s*个分类[，,]\s*(\d+)\s*个关键词")

AUDIT_FIELD_LABELS = {
    "phone": "手机号",
    "display_name": "姓名",
    "email": "邮箱",
    "must_change_password": "首次登录改密",
    "role": "角色",
    "org_id": "所属组织",
    "status": "状态",
    "name": "名称",
    "code": "编码",
    "remark": "备注",
    "platform_name": "平台",
    "shop_name": "店铺名称",
    "shop_color": "店铺颜色",
    "tax_no": "税号",
    "merchant": "商户",
    "registered_address": "注册地址",
    "legal_person": "法人",
    "previous_name": "曾用名",
    "store_long_id": "店铺长 ID",
    "store_short_id": "店铺短 ID",
    "settlement_period": "结算周期",
    "primary_account": "主账号",
    "anchor": "主播",
    "shop_type": "店铺类型",
    "purpose": "用途",
    "former_name": "原店铺名",
    "source_year": "核算年份",
    "source_month": "核算月份",
    "metric_key": "调整指标",
    "metric_label": "调整指标",
    "direction": "调整方向",
    "amount": "调整金额",
    "adjustment_amount": "调整金额",
}

TARGET_LABELS = {
    "organization": "组织",
    "user": "用户",
    "shop": "店铺",
    "category_dict": "分类字典",
    "platform": "平台",
    "transaction_major_category": "资金大分类",
    "transaction_subject": "动账核算科目",
    "transaction_rule": "动账核算规则",
    "summary_adjustment": "汇总调整",
}


def _extract_bracket_values(text: str) -> list[str]:
    return [item.strip() for item in BRACKET_VALUE_RE.findall(text or "") if item.strip()]


def _extract_category_dict_stats(text: str) -> tuple[int, int] | None:
    match = CATEGORY_DICT_STATS_RE.search(text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _quote(text: str) -> str:
    return f"“{text}”"


def _named_object(label: str, name: str | None = None, identifier: int | None = None) -> str:
    if name:
        return f"{label}{_quote(name)}"
    if identifier is not None:
        return f"{label} #{identifier}"
    return label


def _compact_parts(parts: list[str]) -> str:
    return "，".join([part for part in parts if part])


def _format_file_size(bytes_size: int | None) -> str:
    if bytes_size is None or bytes_size < 0:
        return ""
    if bytes_size == 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    index = min(int(math.log(bytes_size, 1024)), len(units) - 1)
    value = bytes_size / (1024 ** index)
    decimals = 0 if index == 0 else 2
    return f"{value:.{decimals}f} {units[index]}"


def _get_mapping(value: dict | None) -> dict[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _select_display_name(*, description: str, target_name: str | None, index: int = 0) -> str | None:
    parts = _extract_bracket_values(description)
    if len(parts) > index:
        return parts[index]
    return target_name


def _select_shop_label(description: str, target_name: str | None) -> str | None:
    parts = _extract_bracket_values(description)
    if len(parts) >= 2:
        return f"{parts[0]} / {parts[1]}"
    if len(parts) == 1:
        return parts[0]
    return target_name


def _format_month(year: Any, month: Any) -> str:
    if year in {None, ""}:
        return ""
    try:
        year_int = int(year)
    except (TypeError, ValueError):
        return str(year)
    if month in {None, ""}:
        return f"{year_int}年"
    try:
        month_int = int(month)
    except (TypeError, ValueError):
        return f"{year_int}年"
    return f"{year_int}-{month_int:02d}"


def _format_range(
    *,
    year: Any = None,
    month: Any = None,
    start_year: Any = None,
    start_month: Any = None,
    end_year: Any = None,
    end_month: Any = None,
) -> str:
    exact = _format_month(year, month)
    if exact:
        return exact
    start = _format_month(start_year, start_month)
    end = _format_month(end_year, end_month)
    if start and end:
        return f"{start} 至 {end}"
    return start or end


def _scope_text(extra_data: dict[str, Any]) -> str:
    scope = str(extra_data.get("scope") or "").strip()
    if scope == "current_page":
        page = extra_data.get("page")
        if page:
            return f"范围：当前页（第 {page} 页）"
        return "范围：当前页"
    if scope == "selected":
        ids = extra_data.get("ids")
        if isinstance(ids, list) and ids:
            return f"范围：选中 {len(ids)} 条"
        return "范围：选中记录"
    return ""


def _export_context(extra_data: dict[str, Any]) -> str:
    parts: list[str] = []
    business_period = _format_range(
        year=extra_data.get("year"),
        month=extra_data.get("month"),
        start_year=extra_data.get("summary_start_year"),
        start_month=extra_data.get("summary_start_month"),
        end_year=extra_data.get("summary_end_year"),
        end_month=extra_data.get("summary_end_month"),
    )
    if business_period:
        parts.append(f"业务：{business_period}")

    accounting_period = _format_range(
        year=extra_data.get("accounting_year") or extra_data.get("source_year"),
        month=extra_data.get("accounting_month") or extra_data.get("source_month"),
        start_year=extra_data.get("accounting_start_year") or extra_data.get("source_start_year"),
        start_month=extra_data.get("accounting_start_month") or extra_data.get("source_start_month"),
        end_year=extra_data.get("accounting_end_year") or extra_data.get("source_end_year"),
        end_month=extra_data.get("accounting_end_month") or extra_data.get("source_end_month"),
    )
    if accounting_period:
        parts.append(f"核算：{accounting_period}")

    upload_period = _format_range(
        year=extra_data.get("upload_accounting_year"),
        month=extra_data.get("upload_accounting_month"),
        start_year=extra_data.get("upload_accounting_start_year"),
        start_month=extra_data.get("upload_accounting_start_month"),
        end_year=extra_data.get("upload_accounting_end_year"),
        end_month=extra_data.get("upload_accounting_end_month"),
    )
    if upload_period:
        parts.append(f"上传月份：{upload_period}")

    platform = extra_data.get("platform") or extra_data.get("platform_name")
    if platform:
        parts.append(f"平台：{platform}")
    report_platform = extra_data.get("report_platform")
    if report_platform:
        parts.append(f"归集平台：{report_platform}")
    shop = extra_data.get("shop") or extra_data.get("shop_name")
    if shop:
        parts.append(f"店铺：{shop}")
    elif extra_data.get("shop_id") is not None:
        parts.append(f"店铺 ID：{extra_data['shop_id']}")
    keyword = extra_data.get("keyword")
    if keyword:
        parts.append(f"关键词：{keyword}")
    status = extra_data.get("status")
    if status:
        parts.append(f"状态：{status}")
    scope = _scope_text(extra_data)
    if scope:
        parts.append(scope)
    return _compact_parts(parts)


def _changed_field_labels(
    old_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
) -> list[str]:
    old_data = _get_mapping(old_value)
    new_data = _get_mapping(new_value)
    if not old_data and not new_data:
        return []

    old_keys = [key for key in old_data.keys() if not str(key).startswith("_")]
    new_keys = [key for key in new_data.keys() if not str(key).startswith("_")]

    if old_data and new_data and set(new_keys).issubset(set(old_keys)) and len(new_keys) < len(old_keys):
        changed_keys = new_keys
    else:
        changed_keys = [
            key
            for key in dict.fromkeys([*old_keys, *new_keys])
            if old_data.get(key) != new_data.get(key)
        ]

    labels: list[str] = []
    for key in changed_keys:
        label = AUDIT_FIELD_LABELS.get(key, key)
        if label not in labels:
            labels.append(label)
    return labels


def _changed_fields_text(old_value: dict[str, Any] | None, new_value: dict[str, Any] | None) -> str:
    labels = _changed_field_labels(old_value, new_value)
    if not labels:
        return ""
    return f"（调整了：{'、'.join(labels[:4])}）"


def _summary_adjustment_name(
    *,
    target_name: str | None,
    old_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
) -> str | None:
    payload = _get_mapping(new_value) or _get_mapping(old_value)
    if payload:
        shop_name = str(payload.get("shop_name") or "").strip()
        period = _format_month(payload.get("source_year"), payload.get("source_month"))
        metric = str(payload.get("metric_label") or payload.get("metric_key") or "").strip()
        parts = [part for part in (shop_name, period, metric) if part]
        if parts:
            return " / ".join(parts)
    return target_name


def _infer_config_operation(description: str) -> str:
    text = description or ""
    if "删除" in text:
        return "delete"
    if "禁用" in text:
        return "disable"
    if "启用" in text:
        return "enable"
    if "修改" in text or "更新" in text:
        return "update"
    if "新增" in text or "创建" in text:
        return "create"
    return "update"


class AuditService:
    @staticmethod
    def render_description(
        *,
        module: str,
        action: str,
        description: str,
        target_type: str | None = None,
        target_id: int | None = None,
        target_name: str | None = None,
        extra_data: dict | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        status: str = "success",
        error_msg: str | None = None,
    ) -> str:
        extra = _get_mapping(extra_data)
        old = _get_mapping(old_value)
        new = _get_mapping(new_value)

        if module == "auth" and action == "login":
            return "登录了系统"
        if module == "auth" and action == "logout":
            return "退出了系统"

        if module == "upload" and action == "upload_start":
            file_count = extra.get("file_count")
            if file_count is None:
                match = re.search(r"共\s*(\d+)\s*个文件", description or "")
                file_count = int(match.group(1)) if match else None
            if file_count:
                return f"发起了批量上传，共 {file_count} 个文件"
            return "发起了批量上传"

        if module == "upload" and action == "upload_file":
            file_name = target_name or _select_display_name(description=description, target_name=None)
            size = _format_file_size(extra.get("file_size"))
            parts = [f"上传了文件{_quote(file_name)}" if file_name else "上传了文件"]
            if size:
                parts.append(f"大小 {size}")
            return "，".join(parts)

        if module == "user":
            user_name = _select_display_name(description=description, target_name=target_name)
            user_object = _named_object("用户", user_name, target_id)
            if action == "create":
                org_name = _select_display_name(description=description, target_name=None, index=1)
                suffix = f"，所属组织：{org_name}" if org_name else ""
                return f"创建了{user_object}{suffix}"
            if action == "update":
                return f"更新了{user_object}{_changed_fields_text(old, new)}"
            if action == "enable":
                return f"启用了{user_object}"
            if action == "disable":
                return f"禁用了{user_object}"
            if action == "reset_pwd":
                return f"重置了{user_object}的登录密码"
            if action == "update_me":
                return f"更新了个人资料{_changed_fields_text(old, new)}"
            if action == "change_pwd":
                return "修改了登录密码"

        if module == "org":
            org_name = target_name or _select_display_name(description=description, target_name=None)
            org_object = _named_object("组织", org_name, target_id)
            if action == "create":
                return f"创建了{org_object}"
            if action == "update":
                return f"更新了{org_object}{_changed_fields_text(old, new)}"
            if action == "enable":
                return f"启用了{org_object}"
            if action == "disable":
                return f"禁用了{org_object}"

        if module == "shop":
            shop_name = _select_shop_label(description, target_name)
            shop_object = _named_object("店铺", shop_name, target_id)
            if action == "create":
                return f"创建了{shop_object}"
            if action == "update":
                return f"更新了{shop_object}{_changed_fields_text(old, new)}"
            if action == "delete":
                return f"删除了{shop_object}"
            if action == "import":
                result = new or {}
                created = result.get("created", 0)
                updated = result.get("updated", 0)
                skipped = result.get("skipped", 0)
                return f"导入了店铺资料（新增 {created} 家，更新 {updated} 家，跳过 {skipped} 家）"

        if module == "transaction_accounting" and action == "upload_file":
            file_name = target_name or _select_display_name(description=description, target_name=None)
            size = _format_file_size(extra.get("file_size"))
            if extra.get("source_upload_file_id"):
                base = f"从统一上传中生成了动账核算文件{_quote(file_name)}" if file_name else "从统一上传中生成了动账核算文件"
            else:
                base = f"上传了动账核算文件{_quote(file_name)}" if file_name else "上传了动账核算文件"
            if size:
                return f"{base}，大小 {size}"
            return base

        if module == "transaction_accounting" and action == "task_rerun":
            return f"重新执行了动账核算任务 #{target_id or extra.get('task_id') or ''}".rstrip()

        if module == "bic_accounting" and action == "upload_file":
            file_name = target_name or _select_display_name(description=description, target_name=None)
            size = _format_file_size(extra.get("file_size"))
            if extra.get("source_upload_file_id"):
                base = f"从统一上传中生成了 BIC 核算文件{_quote(file_name)}" if file_name else "从统一上传中生成了 BIC 核算文件"
            else:
                base = f"上传了 BIC 核算文件{_quote(file_name)}" if file_name else "上传了 BIC 核算文件"
            if size:
                return f"{base}，大小 {size}"
            return base

        if module == "bic_accounting" and action == "task_rerun":
            return f"重新执行了 BIC 核算任务 #{target_id or extra.get('task_id') or ''}".rstrip()

        if module == "transaction_accounting" and action == "config_change":
            op = _infer_config_operation(description)
            label = TARGET_LABELS.get(target_type or "", "配置")
            name = target_name or _select_display_name(description=description, target_name=None)
            obj = _named_object(label, name, target_id)
            verb = {
                "create": "新增了",
                "update": "更新了",
                "delete": "删除了",
                "enable": "启用了",
                "disable": "禁用了",
            }.get(op, "更新了")
            return f"{verb}{obj}"

        if module == "system" and action == "config_change":
            op = _infer_config_operation(description)
            if target_type == "platform":
                name = target_name or _select_display_name(description=description, target_name=None)
                return f"更新了平台{_quote(name)}的配置" if name else "更新了平台配置"
            label = TARGET_LABELS.get(target_type or "", "系统配置")
            name = target_name or _select_display_name(description=description, target_name=None)
            obj = _named_object(label, name, target_id)
            verb = {
                "create": "创建了",
                "update": "更新了",
                "delete": "删除了",
                "enable": "启用了",
                "disable": "禁用了",
            }.get(op, "更新了")
            text = f"{verb}{obj}"
            if target_type == "category_dict" and op == "create":
                stats = _extract_category_dict_stats(description)
                if stats:
                    text = f"{text}（{stats[0]} 个分类，{stats[1]} 个关键词）"
            return text

        if module == "summary_adjustment":
            name = _summary_adjustment_name(
                target_name=target_name,
                old_value=old,
                new_value=new,
            )
            obj = _named_object("汇总调整", name, target_id)
            if action == "create":
                return f"新增了{obj}"
            if action == "update":
                return f"更新了{obj}{_changed_fields_text(old, new)}"
            if action == "delete":
                return f"删除了{obj}"

        if action == "export":
            if module == "transaction_accounting":
                if extra.get("year"):
                    base = f"导出了 {extra['year']} 年动账资金报表"
                elif "明细" in (description or ""):
                    base = "导出了动账汇总明细"
                else:
                    base = "导出了动账汇总报表"
            elif module == "summary":
                has_business_period = any(
                    extra.get(key) is not None
                    for key in (
                        "summary_start_year",
                        "summary_start_month",
                        "summary_end_year",
                        "summary_end_month",
                        "year",
                        "month",
                    )
                )
                base = "导出了财务汇总报表" if has_business_period else "导出了汇总明细报表"
            else:
                base = "导出了数据"
            context = _export_context(extra)
            return f"{base}（{context}）" if context else base

        if status != "success" and error_msg:
            return f"{description}（失败：{error_msg}）"
        return description

    @staticmethod
    def render_log_description(log: OperationLog) -> str:
        return AuditService.render_description(
            module=log.module,
            action=log.action,
            description=log.description,
            target_type=log.target_type,
            target_id=log.target_id,
            target_name=log.target_name,
            extra_data=log.extra_data,
            old_value=log.old_value,
            new_value=log.new_value,
            status=log.status,
            error_msg=log.error_msg,
        )

    @staticmethod
    async def log(
        db: AsyncSession,
        *,
        user_id: int,
        username: str,
        display_name: str,
        org_id: int | None = None,
        module: str,
        action: str,
        description: str,
        ip: str | None = None,
        user_agent: str | None = None,
        method: str | None = None,
        path: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
        target_name: str | None = None,
        extra_data: dict | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        status: str = "success",
        error_msg: str | None = None,
    ) -> OperationLog:
        """Write an operation log entry."""
        rendered_description = AuditService.render_description(
            module=module,
            action=action,
            description=description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            extra_data=extra_data,
            old_value=old_value,
            new_value=new_value,
            status=status,
            error_msg=error_msg,
        )
        log = OperationLog(
            user_id=user_id,
            org_id=org_id,
            username=username,
            display_name=display_name,
            module=module,
            action=action,
            description=rendered_description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            ip=ip,
            user_agent=user_agent,
            method=method,
            path=path,
            old_value=old_value,
            new_value=new_value,
            extra_data=extra_data,
            status=status,
            error_msg=error_msg,
        )
        db.add(log)
        await db.flush()
        return log
