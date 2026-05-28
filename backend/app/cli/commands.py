"""Console command entrypoints managed by pyproject.toml."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import uvicorn
from alembic.config import main as alembic_main


def dev() -> None:
    parser = argparse.ArgumentParser(description="Run the FastAPI development server.")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn reload.")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
    )


def worker() -> None:
    from app.tasks.celery_app import celery_app

    args = sys.argv[1:] or ["--loglevel=info", "--pool=solo"]
    celery_app.worker_main(["worker", *args])


def recover_queued_tasks() -> None:
    parser = argparse.ArgumentParser(description="Re-dispatch queued tasks to Celery and reconcile terminal running tasks.")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    from app.tasks.celery_app import recover_queued_processing_tasks, reconcile_terminal_running_processing_tasks
    from app.tasks.bic_accounting import recover_queued_bic_tasks
    from app.tasks.transaction_accounting import recover_queued_transaction_tasks

    reconciled_count = reconcile_terminal_running_processing_tasks(limit=args.limit)
    processing_count = recover_queued_processing_tasks(limit=args.limit)
    bic_count = recover_queued_bic_tasks(limit=args.limit)
    transaction_count = recover_queued_transaction_tasks(limit=args.limit)
    total = processing_count + bic_count + transaction_count
    print(
        "已处理任务恢复："
        f"修正卡住运行中任务 {reconciled_count} 个；"
        f"重新投递排队任务 {total} 个（通用 {processing_count}，BIC {bic_count}，动账 {transaction_count}）"
    )


def migrate_generate() -> None:
    parser = argparse.ArgumentParser(description="Generate an Alembic migration.")
    parser.add_argument("message", help="Migration message")
    args = parser.parse_args()
    alembic_main(argv=["revision", "--autogenerate", "-m", args.message])


def migrate_upgrade() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "head"
    alembic_main(argv=["upgrade", target])


def migrate_downgrade() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "-1"
    alembic_main(argv=["downgrade", target])


def migrate_current() -> None:
    alembic_main(argv=["current", *sys.argv[1:]])


def migrate_history() -> None:
    args = sys.argv[1:] or ["--verbose"]
    alembic_main(argv=["history", *args])


def migrate_check() -> None:
    alembic_main(argv=["check", *sys.argv[1:]])


def seed_platforms() -> None:
    from scripts.seed_platforms import seed

    asyncio.run(seed())


def seed_users() -> None:
    from scripts.seed_users import seed

    asyncio.run(seed())


def seed_file_specs() -> None:
    from scripts.seed_file_specs import seed

    asyncio.run(seed())


def seed_category_dicts() -> None:
    from scripts.seed_category_dicts import seed

    asyncio.run(seed())


def seed_transaction_accounting_defaults() -> None:
    seed_transaction_accounting_rules()


def seed_transaction_accounting_rules() -> None:
    from scripts.seed_transaction_accounting_defaults import seed

    asyncio.run(seed())


def seed_transaction_major_subjects() -> None:
    from scripts.seed_transaction_major_subjects import seed

    asyncio.run(seed())


async def _seed_all() -> None:
    from scripts.seed_category_dicts import seed as seed_categories
    from scripts.seed_file_specs import seed as seed_specs
    from scripts.seed_platforms import seed as seed_platform_data
    from scripts.seed_transaction_accounting_defaults import (
        seed as seed_transaction_accounting,
    )
    from scripts.seed_transaction_major_subjects import (
        seed as seed_transaction_major_subjects,
    )
    from scripts.seed_users import seed as seed_user_data

    await seed_platform_data()
    await seed_user_data()
    await seed_specs()
    await seed_categories()
    await seed_transaction_accounting()
    await seed_transaction_major_subjects()
    print("\n[OK] All seeds complete.")


def seed_all() -> None:
    asyncio.run(_seed_all())


def ensure_source_partitions() -> None:
    from scripts.ensure_source_partitions import main

    asyncio.run(main())
