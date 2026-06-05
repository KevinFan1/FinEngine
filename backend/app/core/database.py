import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AfterCommitCallback = Callable[[], Awaitable[None] | None]
_AFTER_COMMIT_CALLBACKS_KEY = "after_commit_callbacks"


def register_after_commit(session: AsyncSession, callback: AfterCommitCallback) -> None:
    callbacks = session.info.setdefault(_AFTER_COMMIT_CALLBACKS_KEY, [])
    callbacks.append(callback)


async def run_after_commit_callbacks(session: AsyncSession) -> None:
    while callbacks := session.info.pop(_AFTER_COMMIT_CALLBACKS_KEY, []):
        for callback in callbacks:
            result = callback()
            if inspect.isawaitable(result):
                await result


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
            await run_after_commit_callbacks(session)
            if session.in_transaction():
                await session.commit()
        except Exception:
            await session.rollback()
            raise
