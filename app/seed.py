"""Seed utilities for development and testing."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo import point_value
from app.models.house import House
from app.models.house_amenity import HouseAmenity
from app.models.house_image import HouseImage
from app.models.nearby_university import NearbyUniversity
from app.models.room import Room
from app.models.university import University
from app.models.user import User

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
            coords=point_value(db, latitude, longitude),
        )
        db.add(university)
        created.append(university)

    await db.commit()
    for university in created:
        await db.refresh(university)
    return created


async def seed_sample_data(db: AsyncSession) -> dict[str, list]:
    """Seed universities plus a landlord, houses, rooms, and display metadata."""
    await seed_universities(db)
    landlord_result = await db.execute(
        select(User).where(User.email == "landlord@unistay.local")
    )
    landlord = landlord_result.scalar_one_or_none()
    if landlord is None:
        landlord = User(
            full_name="UniStay Demo Landlord",
            phone="0970000000",
            email="landlord@unistay.local",
            password_hash="seed-password-not-used",
            role="landlord",
            is_verified=True,
        )
        db.add(landlord)
        await db.commit()
        await db.refresh(landlord)

    existing_houses = await db.scalar(select(func.count()).select_from(House))
    if existing_houses:
        result = await db.execute(select(House).order_by(House.created_at.desc()))
        return {"universities": [], "houses": list(result.scalars().all())}

    universities = (await db.execute(select(University))).scalars().all()
    by_initials = {university.initials: university for university in universities}
    samples = [
        {
            "name": "Kalingalinga Student Lodge",
            "location": "Kalingalinga, Lusaka",
            "university": "UNZA",
            "latitude": -15.393,
            "longitude": 28.336,
            "price": 1800,
            "walk_time": "12 min",
            "drive_distance": "2.1 km",
            "rating": 4.5,
            "available_spaces": 6,
            "accent": "#FFFF8C00",
            "amenities": ["WiFi", "Water", "Security", "Study area"],
            "images": [
                "https://images.unsplash.com/photo-1560185127-6ed189bf02f4",
                "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267",
            ],
            "rooms": [
                {"type": "Single", "rent": 1800, "deposit": 900, "available": 3},
                {"type": "Shared", "rent": 1200, "deposit": 600, "available": 3},
            ],
        },
        {
            "name": "Riverside Boarding House",
            "location": "Riverside, Kitwe",
            "university": "CBU",
            "latitude": -12.996,
            "longitude": 28.636,
            "price": 1500,
            "walk_time": "15 min",
            "drive_distance": "2.8 km",
            "rating": 4.2,
            "available_spaces": 4,
            "accent": "#FF2E86AB",
            "amenities": ["WiFi", "Laundry", "Parking"],
            "images": [
                "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
            ],
            "rooms": [
                {"type": "Single", "rent": 1500, "deposit": 750, "available": 2},
                {"type": "Shared", "rent": 950, "deposit": 500, "available": 2},
            ],
        },
    ]

    created: list[House] = []
    for sample in samples:
        university = by_initials.get(sample["university"])
        house = House(
            landlord_id=landlord.id,
            name=sample["name"],
            location=sample["location"],
            coords=point_value(db, sample["latitude"], sample["longitude"]),
            university_id=university.id if university else None,
            price=sample["price"],
            walk_time=sample["walk_time"],
            drive_distance=sample["drive_distance"],
            rating=sample["rating"],
            available_spaces=sample["available_spaces"],
            accent=sample["accent"],
            payment_methods=["mobile_money", "cash"],
        )
        house.amenities = [HouseAmenity(name=name) for name in sample["amenities"]]
        house.images = [
            HouseImage(url=url, order=index)
            for index, url in enumerate(sample["images"])
        ]
        house.nearby_universities = [
            NearbyUniversity(
                name=university.name if university else sample["university"],
                distance=sample["drive_distance"],
            )
        ]
        house.rooms = [
            Room(
                type=room["type"],
                rent=room["rent"],
                deposit=room["deposit"],
                available=room["available"],
                features=["Bed", "Wardrobe", "Desk"],
            )
            for room in sample["rooms"]
        ]
        db.add(house)
        created.append(house)

    await db.commit()
    for house in created:
        await db.refresh(house)
    return {"universities": universities, "houses": created}
