"""Dependency-injection providers for repositories, clients, and services.

Routers should depend on these provider functions (e.g. ``Depends(get_house_service)``)
instead of constructing services inline. This keeps wiring centralised, makes
mocking in tests a single ``app.dependency_overrides`` entry, and lets expensive
clients (``LencoClient``, ``GoogleMapsClient``) be constructed once per process
rather than per request.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.google_maps_client import GoogleMapsClient
from app.clients.lenco_client import LencoClient
from app.config import settings
from app.dependencies import get_db
from app.repositories.booking_repo import BookingRepository
from app.repositories.eta_cache_repo import EtaCacheRepository
from app.repositories.favorite_repo import FavoriteRepository
from app.repositories.house_repo import HouseRepository
from app.repositories.landlord_payment_detail_repo import LandlordPaymentDetailRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.room_repo import RoomRepository
from app.repositories.university_repo import UniversityRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
from app.services.favorite_service import FavoriteService
from app.services.geo_service import GeoService
from app.services.house_service import HouseService
from app.services.landlord_service import LandlordService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.services.university_service import UniversityService
from app.services.user_service import UserService


# --- Clients (process-scoped singletons) -----------------------------------


@lru_cache(maxsize=1)
def get_lenco_client() -> LencoClient:
    """Return a process-wide ``LencoClient`` bound to app settings."""
    return LencoClient(settings)


@lru_cache(maxsize=1)
def get_google_maps_client() -> GoogleMapsClient:
    """Return a process-wide ``GoogleMapsClient``.

    Tests can override via ``app.dependency_overrides`` rather than rebuilding
    the client on every request.
    """
    return GoogleMapsClient()


def reset_client_cache() -> None:
    """Clear the singleton client caches (used by tests)."""
    get_lenco_client.cache_clear()
    get_google_maps_client.cache_clear()


# --- Repositories (request-scoped) -----------------------------------------


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_house_repository(db: AsyncSession = Depends(get_db)) -> HouseRepository:
    return HouseRepository(db)


def get_room_repository(db: AsyncSession = Depends(get_db)) -> RoomRepository:
    return RoomRepository(db)


def get_booking_repository(db: AsyncSession = Depends(get_db)) -> BookingRepository:
    return BookingRepository(db)


def get_payment_repository(db: AsyncSession = Depends(get_db)) -> PaymentRepository:
    return PaymentRepository(db)


def get_notification_repository(
    db: AsyncSession = Depends(get_db),
) -> NotificationRepository:
    return NotificationRepository(db)


def get_favorite_repository(db: AsyncSession = Depends(get_db)) -> FavoriteRepository:
    return FavoriteRepository(db)


def get_university_repository(
    db: AsyncSession = Depends(get_db),
) -> UniversityRepository:
    return UniversityRepository(db)


def get_eta_cache_repository(
    db: AsyncSession = Depends(get_db),
) -> EtaCacheRepository:
    return EtaCacheRepository(db)


def get_landlord_payment_detail_repository(
    db: AsyncSession = Depends(get_db),
) -> LandlordPaymentDetailRepository:
    return LandlordPaymentDetailRepository(db)


# --- Services (request-scoped) ---------------------------------------------


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(user_repo)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repo)


def get_house_service(
    house_repo: HouseRepository = Depends(get_house_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
) -> HouseService:
    return HouseService(house_repo, room_repo)


def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repository),
    house_repo: HouseRepository = Depends(get_house_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    payment_repo: PaymentRepository = Depends(get_payment_repository),
) -> BookingService:
    return BookingService(
        booking_repo,
        house_repo,
        room_repo,
        notification_repo,
        payment_repo,
    )


def get_payment_service(
    payment_repo: PaymentRepository = Depends(get_payment_repository),
    lenco_client: LencoClient = Depends(get_lenco_client),
    booking_repo: BookingRepository = Depends(get_booking_repository),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> PaymentService:
    return PaymentService(
        payment_repo,
        lenco_client,
        booking_repo,
        notification_repo,
    )


def get_favorite_service(
    favorite_repo: FavoriteRepository = Depends(get_favorite_repository),
    house_repo: HouseRepository = Depends(get_house_repository),
) -> FavoriteService:
    return FavoriteService(favorite_repo, house_repo)


def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> NotificationService:
    return NotificationService(notification_repo)


def get_university_service(
    university_repo: UniversityRepository = Depends(get_university_repository),
) -> UniversityService:
    return UniversityService(university_repo)


def get_landlord_service(
    house_repo: HouseRepository = Depends(get_house_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
    booking_repo: BookingRepository = Depends(get_booking_repository),
    payment_detail_repo: LandlordPaymentDetailRepository = Depends(
        get_landlord_payment_detail_repository
    ),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> LandlordService:
    return LandlordService(
        house_repo,
        room_repo,
        booking_repo,
        payment_detail_repo,
        notification_repo,
    )


def get_geo_service(
    house_repo: HouseRepository = Depends(get_house_repository),
    university_repo: UniversityRepository = Depends(get_university_repository),
    eta_repo: EtaCacheRepository = Depends(get_eta_cache_repository),
    maps_client: GoogleMapsClient = Depends(get_google_maps_client),
) -> GeoService:
    return GeoService(
        house_repo=house_repo,
        university_repo=university_repo,
        eta_repo=eta_repo,
        maps_client=maps_client,
    )


def get_places_geo_service(
    university_repo: UniversityRepository = Depends(get_university_repository),
    maps_client: GoogleMapsClient = Depends(get_google_maps_client),
) -> GeoService:
    """Return a ``GeoService`` configured for Places proxy routes (no house/eta repos)."""
    return GeoService(
        house_repo=None,
        university_repo=university_repo,
        eta_repo=None,
        maps_client=maps_client,
    )
