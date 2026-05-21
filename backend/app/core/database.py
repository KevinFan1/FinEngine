import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,  # Increased from 10 for better concurrency
    max_overflow=30,  # Increased from 20
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour to prevent stale connections
    pool_timeout=30,  # Wait up to 30 seconds for a connection
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
