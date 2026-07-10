"""Server-side Google Maps Platform client."""

import base64
import hashlib
import hmac
import urllib.parse
from typing import Any

import httpx

from app.config import settings
from app.exceptions import AppError


class GoogleMapsError(AppError):
    def __init__(self, message: str = "Google Maps error", status_code: int = 502):
        super().__init__(message, status_code)


class GoogleMapsClient:
    BASE_URL = "https://maps.googleapis.com/maps/api"
    PLACES_BASE_URL = "https://places.googleapis.com/v1"
    ROUTES_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.google_maps_server_key

    def _redact_url(self, url: str) -> str:
        if not self.api_key:
            return url
        return url.replace(self.api_key, "<REDACTED>")

    async def autocomplete(
        self, *, input_text: str, session_token: str, region: str | None = None
    ) -> dict:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        url = f"{self.PLACES_BASE_URL}/places:autocomplete"
        body = {
            "input": input_text,
            "sessionToken": session_token,
            "regionCode": region or settings.google_maps_places_region,
            "locationBias": {
                "circle": {
                    "center": {"latitude": -15.4167, "longitude": 28.2833},
                    "radius": 50000.0,
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "suggestions.placePrediction.text,suggestions.placePrediction.placeId",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(url, json=body, headers=headers)
        if response.status_code >= 400:
            raise GoogleMapsError(
                f"Places autocomplete failed (HTTP {response.status_code})"
            )
        return response.json()

    async def place_details(self, *, place_id: str, session_token: str) -> dict:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        encoded_place_id = urllib.parse.quote(place_id, safe="")
        url = f"{self.PLACES_BASE_URL}/places/{encoded_place_id}"
        params = {"sessionToken": session_token}
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,formattedAddress,location",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, params=params, headers=headers)
        if response.status_code >= 400:
            raise GoogleMapsError(
                f"Place details failed (HTTP {response.status_code})"
            )
        return response.json()

    async def compute_route_matrix(
        self, *, origin: dict, destination: dict, mode: str = "DRIVE"
    ) -> dict | list:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        body = {
            "origins": [{"waypoint": {"location": {"latLng": origin}}}],
            "destinations": [{"waypoint": {"location": {"latLng": destination}}}],
            "travelMode": mode,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,condition",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(self.ROUTES_URL, json=body, headers=headers)
        if response.status_code >= 400:
            raise GoogleMapsError(f"Routes API failed (HTTP {response.status_code})")
        return response.json()

    async def reverse_geocode(self, latitude: float, longitude: float) -> str | None:
        if not self.api_key:
            return None

        url = f"{self.BASE_URL}/geocode/json"
        params = {"latlng": f"{latitude},{longitude}", "key": self.api_key}
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, params=params)
        if response.status_code >= 400:
            return None
        data = response.json()
        results = data.get("results") or []
        return results[0].get("formatted_address") if results else None

    def static_map_url(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 15,
        width: int = 400,
        height: int = 250,
    ) -> str:
        if not self.api_key:
            raise GoogleMapsError("Google Maps server key is not configured")

        params = {
            "center": f"{latitude},{longitude}",
            "zoom": zoom,
            "size": f"{width}x{height}",
            "markers": f"color:red|{latitude},{longitude}",
            "key": self.api_key,
        }
        url = f"{self.BASE_URL}/staticmap?" + urllib.parse.urlencode(params)
        return self._sign_url(url)

    def _sign_url(self, url: str) -> str:
        secret = settings.google_maps_signing_secret
        if not secret:
            return url
        parsed = urllib.parse.urlparse(url)
        path_and_query = parsed.path + "?" + parsed.query
        decoded_secret = base64.urlsafe_b64decode(secret + "==")
        signature = hmac.new(
            decoded_secret, path_and_query.encode("utf-8"), hashlib.sha1
        ).digest()
        encoded_signature = (
            base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        )
        return f"{url}&signature={encoded_signature}"
