"""Pydantic schemas for house listing and detail responses."""

from pydantic import BaseModel, ConfigDict, Field


class NearbyUniversityResponse(BaseModel):
    """Nearby university display item."""

    name: str
    distance: str


class HouseResponse(BaseModel):
    """Public house representation for listings and detail views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    location: str
    university: str | None
    price: int
    walk_time: str | None
    drive_distance: str | None
    rating: float
    available_spaces: int
    accent: str
    amenities: list[str]
    image_urls: list[str]
    payment_methods: list[str]
    nearby_universities: list[NearbyUniversityResponse]


class HouseListResponse(BaseModel):
    """Paginated list of houses."""

    items: list[HouseResponse]
    total: int
    page: int
    limit: int
    pages: int


class HouseCreateRequest(BaseModel):
    """Request body for landlord house creation."""

    name: str = Field(..., min_length=2, max_length=255)
    location: str = Field(..., min_length=2, max_length=255)
    university_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    price: int = Field(..., ge=0)
    walk_time: str | None = Field(default=None, max_length=50)
    drive_distance: str | None = Field(default=None, max_length=50)
    rating: float = Field(default=0.0, ge=0, le=5)
    available_spaces: int = Field(default=0, ge=0)
    accent: str = Field(default="#FFFF8C00", max_length=9)
    payment_methods: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    nearby_universities: list[NearbyUniversityResponse] = Field(default_factory=list)
    rooms: list[dict] = Field(default_factory=list)


class HouseUpdateRequest(BaseModel):
    """Request body for landlord house updates."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    location: str | None = Field(default=None, min_length=2, max_length=255)
    university_id: str | None = None
    price: int | None = Field(default=None, ge=0)
    walk_time: str | None = Field(default=None, max_length=50)
    drive_distance: str | None = Field(default=None, max_length=50)
    rating: float | None = Field(default=None, ge=0, le=5)
    available_spaces: int | None = Field(default=None, ge=0)
    accent: str | None = Field(default=None, max_length=9)
    payment_methods: list[str] | None = None


class AmenitiesUpdateRequest(BaseModel):
    """Request body for replacing house amenities."""

    amenities: list[str] = Field(..., min_length=0)


class HouseSearchParams(BaseModel):
    """Query parameters for house search/listing."""

    university: str | None = Field(None, description="University ID or initials")
    q: str | None = Field(None, description="Search term for name or location")
    amenities: list[str] | None = Field(None, description="Required amenities")
    min_price: int | None = Field(None, ge=0)
    max_price: int | None = Field(None, ge=0)
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
