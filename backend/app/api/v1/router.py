from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    bic_accounting,
    category_dicts,
    export_jobs,
    file_specs,
    health,
    merchant_reconciliation,
    organizations,
    oss,
    platforms,
    quota,
    shops,
    summary_adjustments,
    summaries,
    tasks,
    transaction_accounting,
    uploads,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["组织管理"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(quota.router, tags=["配额管理"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["上传中心"])
api_router.include_router(oss.router, prefix="/oss", tags=["OSS 存储"])
api_router.include_router(export_jobs.router, prefix="/export-jobs", tags=["下载中心"])
api_router.include_router(file_specs.router, prefix="/file-specs", tags=["文件规格"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(summaries.router, prefix="/summaries", tags=["汇总报表"])
api_router.include_router(summary_adjustments.router, prefix="/summary-adjustments", tags=["汇总调整"])
api_router.include_router(transaction_accounting.router, prefix="/transaction-accounting", tags=["动账核算"])
api_router.include_router(bic_accounting.router, prefix="/bic-accounting", tags=["BIC核算"])
api_router.include_router(merchant_reconciliation.router, prefix="/merchant-reconciliation", tags=["商家对账"])
api_router.include_router(platforms.router, prefix="/platforms", tags=["平台配置"])
api_router.include_router(category_dicts.router, prefix="/category-dicts", tags=["分类字典"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["操作日志"])
api_router.include_router(shops.router, prefix="/shops", tags=["店铺管理"])
