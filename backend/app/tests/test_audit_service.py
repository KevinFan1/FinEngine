import pytest

from app.models.operation_log import OperationLog
from app.services.audit_service import AuditService


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[OperationLog] = []

    def add(self, instance: OperationLog) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        return None


def test_render_description_formats_user_update_with_changed_fields() -> None:
    text = AuditService.render_description(
        module="user",
        action="update",
        description="管理员修改用户 [张三] 信息",
        target_type="user",
        target_id=18,
        target_name="zhangsan",
        old_value={"phone": "13800000000", "role": "member", "status": 1},
        new_value={"phone": "13900000000", "role": "org_admin", "status": 1},
    )

    assert text == "更新了用户“张三”（调整了：手机号、角色）"


def test_render_description_formats_summary_export_with_filters() -> None:
    text = AuditService.render_description(
        module="summary",
        action="export",
        description="用户 [管理员] 导出汇总报表",
        extra_data={
            "summary_start_year": 2026,
            "summary_start_month": 1,
            "summary_end_year": 2026,
            "summary_end_month": 3,
            "source_year": 2026,
            "source_month": 4,
            "platform": "抖音",
            "shop": "旗舰店",
            "scope": "selected",
            "ids": [11, 12, 13],
        },
    )

    assert text == "导出了财务汇总报表（业务：2026-01 至 2026-03，核算：2026-04，平台：抖音，店铺：旗舰店，范围：选中 3 条）"


def test_render_log_description_formats_historical_category_dict_log() -> None:
    log = OperationLog(
        user_id=1,
        org_id=None,
        username="superadmin",
        display_name="超级管理员",
        module="system",
        action="config_change",
        description="超管创建分类字典 [退款分类]，3 个分类，18 个关键词",
        target_type="category_dict",
        target_id=9,
        target_name="退款分类",
        status="success",
    )

    assert AuditService.render_log_description(log) == "创建了分类字典“退款分类”（3 个分类，18 个关键词）"


def test_render_description_formats_upload_file_with_size() -> None:
    text = AuditService.render_description(
        module="upload",
        action="upload_file",
        description="用户 [李雷] 上传文件 [对账单.xlsx]",
        target_type="upload_file",
        target_id=3,
        target_name="对账单.xlsx",
        extra_data={"file_size": 40 * 1024 * 1024},
    )

    assert text == "上传了文件“对账单.xlsx”，大小 40.00 MB"


@pytest.mark.asyncio
async def test_log_persists_humanized_description() -> None:
    session = _FakeSession()

    log = await AuditService.log(
        session,  # type: ignore[arg-type]
        user_id=1,
        username="admin",
        display_name="管理员",
        org_id=1,
        module="upload",
        action="upload_start",
        description="用户 [管理员] 发起批量上传，共 6 个文件",
        extra_data={"file_count": 6},
    )

    assert log.description == "发起了批量上传，共 6 个文件"
    assert session.added[0].description == "发起了批量上传，共 6 个文件"
