"""Base repository providing common database session access.

The base repository exposes ``flush`` (write pending changes to the DB without
committing) and ``commit`` so services can compose multiple repository writes
into a single transactional unit of work. Subclasses should use ``flush`` for
intermediate writes that must be persisted inside a service-controlled
transaction, and let the service call ``commit`` once the unit of work is
complete. The simplest repos still expose ``commit``-based methods for
backwards compatibility with single-aggregate writes.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Generic repository that stores an async SQLAlchemy session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def flush(self) -> None:
        """Flush pending changes without committing.

        Lets a service stage multiple repo writes against the same session and
        commit them as one atomic unit of work.
        """
        await self.db.flush()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.db.rollback()
