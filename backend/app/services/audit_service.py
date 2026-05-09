from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog


class AuditService:
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
        log = OperationLog(
            user_id=user_id,
            org_id=org_id,
            username=username,
            display_name=display_name,
            module=module,
            action=action,
            description=description,
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
