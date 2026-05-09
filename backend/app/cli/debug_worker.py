"""Debug worker processing with a local Excel/CSV file.

This script creates a debug upload batch/file/task in the database and then
runs the real worker processing function in-process. It bypasses Celery and
OSS by temporarily replacing OSS download with a local file copy.

Usage:
    cd backend
    uv run debug-worker /path/to/26年02月_动账_宝蕴天工.xlsx
    uv run debug-worker /path/to/26年02月_gmv_快手店铺.csv --platform kuaishou
    uv run debug-worker /path/to/file.xlsx --platform douyin --shop 宝蕴天工
    uv run debug-worker --file-id 12 /path/to/file.csv
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session_factory, engine
from app.models.organization import Organization
from app.models.shop import Shop
from app.models.task import ProcessingTask
from app.models.upload import UploadBatch, UploadFile
from app.models.user import User
from app.tasks.celery_app import _process_file_platform_async


@dataclass
class ParsedFilename:
    year: int | None
    month: int | None
    type_code: str | None
    shop: str | None


class DebugTaskRequest:
    id = "debug-worker-local"


class DebugTaskInstance:
    request = DebugTaskRequest()


def parse_filename(filename: str) -> ParsedFilename:
    """Parse frontend-compatible filenames: YY/YYYY年MM月_类型_店铺.ext."""
    stem = Path(filename).stem
    normalized = stem.replace(" ", "_")
    parts = normalized.split("_", 2)
    if len(parts) != 3:
        return ParsedFilename(None, None, None, None)

    ym, type_code, shop = parts
    lower_type = type_code.lower()
    normalized_type = lower_type if lower_type in {"bic", "gmv"} else type_code
    if "年" not in ym or "月" not in ym:
        return ParsedFilename(None, None, normalized_type, shop.strip() or None)

    year_text, month_part = ym.split("年", 1)
    month_text = month_part.split("月", 1)[0]
    try:
        year = 2000 + int(year_text) if len(year_text) == 2 else int(year_text)
        month = int(month_text)
    except ValueError:
        return ParsedFilename(None, None, normalized_type, shop.strip() or None)

    if month < 1 or month > 12:
        return ParsedFilename(None, None, normalized_type, shop.strip() or None)

    return ParsedFilename(year, month, normalized_type, shop.strip() or None)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def pick_org_and_user(org_id: int | None, user_id: int | None) -> tuple[Organization, User]:
    async with async_session_factory() as db:
        if org_id is not None:
            org_result = await db.execute(select(Organization).where(Organization.id == org_id, Organization.is_deleted.is_(False)))
        else:
            org_result = await db.execute(select(Organization).where(Organization.code == "default", Organization.is_deleted.is_(False)))
            if org_result.scalar_one_or_none() is None:
                org_result = await db.execute(select(Organization).where(Organization.is_deleted.is_(False)).order_by(Organization.id).limit(1))
            else:
                org_result = await db.execute(select(Organization).where(Organization.code == "default", Organization.is_deleted.is_(False)))
        org = org_result.scalar_one_or_none()
        if org is None:
            raise RuntimeError("找不到组织，请先执行 uv run python -m scripts.seed_users，或传 --org-id")

        if user_id is not None:
            user_result = await db.execute(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
        else:
            user_result = await db.execute(
                select(User)
                .where(User.org_id == org.id, User.is_deleted.is_(False))
                .order_by(User.role == "org_admin", User.id)
                .limit(1)
            )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise RuntimeError("找不到用户，请先执行 uv run python -m scripts.seed_users，或传 --user-id")

        return org, user


async def create_debug_records(
    *,
    file_path: Path,
    org_id: int | None,
    user_id: int | None,
    platform_code: str,
    shop_name: str,
    parsed: ParsedFilename,
) -> tuple[UploadFile, ProcessingTask]:
    org, user = await pick_org_and_user(org_id, user_id)

    async with async_session_factory() as db:
        batch = UploadBatch(
            org_id=org.id,
            user_id=user.id,
            file_count=1,
            status="debug",
            remark="debug_worker.py local run",
        )
        db.add(batch)
        await db.flush()

        shop_result = await db.execute(
            select(Shop).where(
                Shop.org_id == org.id,
                Shop.platform_name == platform_code,
                Shop.shop_name == shop_name,
                Shop.is_deleted.is_(False),
            )
        )
        shop = shop_result.scalar_one_or_none()
        if shop is None:
            shop = Shop(org_id=org.id, platform_name=platform_code, shop_name=shop_name)
            db.add(shop)
            await db.flush()

        upload_file = UploadFile(
            batch_id=batch.id,
            org_id=org.id,
            user_id=user.id,
            shop_id=shop.id,
            original_name=file_path.name,
            oss_key=f"debug/local/{file_path.name}",
            file_size=file_path.stat().st_size,
            file_hash=sha256_file(file_path),
            parsed_year=parsed.year,
            parsed_month=parsed.month,
            parsed_type=parsed.type_code,
            parsed_shop=shop_name,
            detected_platform=platform_code,
            status="uploaded",
        )
        db.add(upload_file)
        await db.flush()

        task = ProcessingTask(
            file_id=upload_file.id,
            org_id=org.id,
            user_id=user.id,
            status="queued",
            progress=0,
        )
        db.add(task)
        await db.commit()
        await db.refresh(upload_file)
        await db.refresh(task)
        return upload_file, task


async def load_existing_file(file_id: int) -> tuple[UploadFile, ProcessingTask]:
    async with async_session_factory() as db:
        file_result = await db.execute(select(UploadFile).where(UploadFile.id == file_id, UploadFile.is_deleted.is_(False)))
        upload_file = file_result.scalar_one_or_none()
        if upload_file is None:
            raise RuntimeError(f"fin_upload_files.id={file_id} 不存在")

        task_result = await db.execute(
            select(ProcessingTask)
            .where(ProcessingTask.file_id == file_id, ProcessingTask.is_deleted.is_(False))
            .order_by(ProcessingTask.id.desc())
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            task = ProcessingTask(
                file_id=upload_file.id,
                org_id=upload_file.org_id,
                user_id=upload_file.user_id,
                status="queued",
                progress=0,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
        return upload_file, task


async def reset_task_for_debug(file_id: int) -> None:
    async with async_session_factory() as db:
        file_result = await db.execute(select(UploadFile).where(UploadFile.id == file_id, UploadFile.is_deleted.is_(False)))
        upload_file = file_result.scalar_one()
        task_result = await db.execute(
            select(ProcessingTask)
            .where(ProcessingTask.file_id == file_id, ProcessingTask.is_deleted.is_(False))
            .order_by(ProcessingTask.id.desc())
        )
        task = task_result.scalar_one()

        upload_file.status = "uploaded"
        upload_file.error_message = None
        task.status = "queued"
        task.progress = 0
        task.celery_task_id = None
        task.processed_rows = 0
        task.success_rows = 0
        task.failed_rows = 0
        task.error_message = None
        task.result_summary = None
        task.started_at = None
        task.finished_at = None
        await db.commit()


def patch_oss_download(local_file: Path):
    from app.services.oss_service import oss_service

    original = oss_service.download_to_temp

    def download_to_temp(_oss_key: str, temp_path: str) -> str:
        shutil.copyfile(local_file, temp_path)
        return temp_path

    oss_service.download_to_temp = download_to_temp
    return oss_service, original


async def run_debug(args: argparse.Namespace) -> None:
    file_path = args.local_file.expanduser().resolve()
    if not file_path.exists():
        raise RuntimeError(f"本地文件不存在: {file_path}")
    if not file_path.is_file():
        raise RuntimeError(f"不是文件: {file_path}")

    parsed = parse_filename(file_path.name)
    platform_code = args.platform
    shop_name = args.shop or parsed.shop
    if not shop_name:
        raise RuntimeError("无法从文件名识别店铺名，请传 --shop")

    if args.file_id is not None:
        upload_file, task = await load_existing_file(args.file_id)
        platform_code = args.platform or upload_file.detected_platform or platform_code
        shop_name = args.shop or upload_file.parsed_shop or shop_name
        await reset_task_for_debug(upload_file.id)
    else:
        upload_file, task = await create_debug_records(
            file_path=file_path,
            org_id=args.org_id,
            user_id=args.user_id,
            platform_code=platform_code,
            shop_name=shop_name,
            parsed=parsed,
        )

    print(f"[debug] local_file={file_path}")
    print(f"[debug] upload_file_id={upload_file.id} task_id={task.id} org_id={upload_file.org_id}")
    print(f"[debug] platform={platform_code} shop={shop_name}")

    oss_service, original_download = patch_oss_download(file_path)
    processing_error: Exception | None = None
    try:
        await _process_file_platform_async(
            DebugTaskInstance(),
            file_id=upload_file.id,
            oss_key=upload_file.oss_key,
            org_id=upload_file.org_id,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_id=upload_file.shop_id,
        )
    except Exception as exc:
        processing_error = exc
    finally:
        oss_service.download_to_temp = original_download

    async with async_session_factory() as db:
        result = await db.execute(
            select(ProcessingTask)
            .where(ProcessingTask.file_id == upload_file.id, ProcessingTask.is_deleted.is_(False))
            .order_by(ProcessingTask.id.desc())
        )
        task = result.scalar_one()
        print("[result]")
        print(f"  status={task.status} progress={task.progress}")
        print(f"  rows processed={task.processed_rows} success={task.success_rows} failed={task.failed_rows}")
        print(f"  error={task.error_message}")
        print(f"  summary={task.result_summary}")

    if processing_error is not None:
        raise processing_error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run worker processing logic against a local Excel/CSV file.")
    parser.add_argument("local_file", type=Path, help="本地 Excel/CSV 文件路径")
    parser.add_argument("--file-id", type=int, help="复用已有 fin_upload_files.id；不传则自动创建 debug 记录")
    parser.add_argument("--platform", default="douyin", help="平台编码，默认 douyin")
    parser.add_argument("--shop", help="店铺名；不传则尝试从文件名解析")
    parser.add_argument("--org-id", type=int, help="创建 debug 记录时使用的组织 ID")
    parser.add_argument("--user-id", type=int, help="创建 debug 记录时使用的用户 ID")
    return parser


async def async_main() -> None:
    args = build_parser().parse_args()
    try:
        await run_debug(args)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
