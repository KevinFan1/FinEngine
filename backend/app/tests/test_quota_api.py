from decimal import Decimal

from app.api.v1.quota import UpdateQuotaRequest


def test_update_quota_request_accepts_decimal_storage_gb() -> None:
    body = UpdateQuotaRequest(max_storage_gb=Decimal("0.5"))

    assert body.max_storage_gb == Decimal("0.5")
    assert int(body.max_storage_gb * 1024 * 1024 * 1024) == 536870912
