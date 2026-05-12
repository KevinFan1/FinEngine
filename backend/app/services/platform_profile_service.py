"""Platform hierarchy helpers.

The source platform is the uploaded file's detected platform. The report
platform is the parent platform used by summary reports. The order scope keeps
order-index matching shared inside one business platform family.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import Platform


TAOBAO_FAMILY = {"taobao", "tmall", "alipay", "qianniu"}
PLATFORM_FAMILY_FALLBACKS: dict[str, dict[str, str]] = {
    "taobao": {"report_platform_code": "taobao", "order_scope_code": "taobao", "processor_code": "taobao"},
    "tmall": {"report_platform_code": "taobao", "order_scope_code": "taobao", "processor_code": "tmall"},
    "alipay": {"report_platform_code": "taobao", "order_scope_code": "taobao", "processor_code": "alipay"},
    "qianniu": {"report_platform_code": "taobao", "order_scope_code": "taobao", "processor_code": "qianniu"},
}


@dataclass(frozen=True)
class PlatformProfile:
    source_platform_code: str
    report_platform_code: str
    processor_code: str
    order_scope_code: str

    @property
    def is_sub_platform(self) -> bool:
        return self.source_platform_code != self.report_platform_code


def fallback_platform_profile(platform_code: str) -> PlatformProfile:
    code = (platform_code or "").strip()
    family = PLATFORM_FAMILY_FALLBACKS.get(code)
    if family:
        return PlatformProfile(
            source_platform_code=code,
            report_platform_code=family["report_platform_code"],
            processor_code=family["processor_code"],
            order_scope_code=family["order_scope_code"],
        )
    return PlatformProfile(
        source_platform_code=code,
        report_platform_code=code,
        processor_code=code,
        order_scope_code=code,
    )


async def resolve_platform_profile(db: AsyncSession, platform_code: str) -> PlatformProfile:
    code = (platform_code or "").strip()
    if not code:
        return fallback_platform_profile(code)

    result = await db.execute(select(Platform).where(Platform.code == code, Platform.is_deleted.is_(False)))
    platform = result.scalar_one_or_none()
    if platform is None:
        return fallback_platform_profile(code)

    report_platform_code = (platform.parent_code or platform.code).strip()
    processor_code = (platform.processor_code or platform.code).strip()
    order_scope_code = (platform.order_scope_code or report_platform_code).strip()
    return PlatformProfile(
        source_platform_code=platform.code,
        report_platform_code=report_platform_code,
        processor_code=processor_code,
        order_scope_code=order_scope_code,
    )
