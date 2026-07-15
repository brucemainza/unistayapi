"""Pydantic schemas for geolocation endpoints."""

from pydantic import BaseModel, Field


class EtaRequest(BaseModel):
    """Query parameters for ETA requests."""

    university_id: str
    mode: str = Field(default="DRIVE", pattern=r"^(WALK|DRIVE)$")


class EtaResponse(BaseModel):
    """ETA response."""

    duration_s: int
    distance_m: int
    mode: str
    cached: bool


class AutocompleteSuggestion(BaseModel):
    """A single autocomplete suggestion."""

    text: str
    place_id: str


class PlacesAutocompleteResponse(BaseModel):
    """Places autocomplete response."""

    suggestions: list[AutocompleteSuggestion]


class PlaceLocation(BaseModel):
    """Place location coordinates."""

    latitude: float
    longitude: float


class PlaceDetailsResponse(BaseModel):
    """Place details response."""

    place_id: str
    formatted_address: str
    location: PlaceLocation
