"""Seed utilities for development and testing."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.university import University

# Flutter mock data: Zambian universities with approximate campus coordinates.
ZAMBIAN_UNIVERSITIES: Sequence[tuple[str, str, float, float]] = (
    # (name, initials, latitude, longitude)
    ("University of Zambia", "UNZA", -15.3918, 28.3296),
    ("Copperbelt University", "CBU", -12.9989, 28.6333),
    ("Mulungushi University", "MU", -14.4443, 28.4465),
    ("Lusaka Apex Medical University", "LAMU", -15.4167, 28.2833),
    ("Cavendish University Zambia", "CUZ", -15.4180, 28.2850),
    ("University of Lusaka", "UNILUS", -15.4140, 28.2810),
    ("Zambia Open University", "ZAOU", -15.4200, 28.2870),
    ("Northrise University", "NU", -12.9687, 28.6364),
    ("Texila American University Zambia", "TAUZ", -15.4220, 28.2890),
    ("Information and Communication University", "ICU", -15.4160, 28.2840),
)


async def seed_universities(db: AsyncSession) -> list[University]:
    """Insert the default Zambian universities if the table is empty."""
    result = await db.execute(select(func.count()).select_from(University))
    count = result.scalar()
    if count:
        return []

    created: list[University] = []
    for name, initials, latitude, longitude in ZAMBIAN_UNIVERSITIES:
        university = University(
            name=name,
            initials=initials,
            coords=func.ST_GeogFromText(f"POINT({longitude} {latitude})"),
        )
        db.add(university)
        created.append(university)

    await db.commit()
    for university in created:
        await db.refresh(university)
    return created
