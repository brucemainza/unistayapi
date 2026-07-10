"""Base repository providing common database session access."""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Generic repository that stores an async SQLAlchemy session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
