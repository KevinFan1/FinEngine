from datetime import datetime

from app.services.order_index_service import OrderIndexService


def test_order_index_upsert_rows_are_chunked_under_asyncpg_argument_limit() -> None:
    rows = OrderIndexService._dedupe_rows(
        org_id=1,
        shop_id=2,
        platform_code="xiaohongshu",
        orders=[
            {"order_no": f"xhs-{index}", "order_created_at": datetime(2026, 4, 1, 12, 0, 0)}
            for index in range(3000)
        ],
        source_file_id=10,
    )

    chunks = OrderIndexService._chunk_rows_for_upsert(rows)
    max_bind_count = max(len(chunk) * len(chunk[0]) for chunk in chunks)

    assert len(chunks) == 2
    assert max_bind_count <= OrderIndexService.UPSERT_MAX_QUERY_ARGS
    assert sum(len(chunk) for chunk in chunks) == len(rows)
