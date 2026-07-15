"""Server-side Google Maps Platform client."""

import base64
import hashlib
import hmac
import json
import urllib.parse
from typing import Any

import httpx

from app.config import settings
from app.exceptions import AppError
from app.logging_config import get_logger

logger = get_logger(__name__)


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

    def _log_upstream_error(self, operation: str, response: httpx.Response) -> None:
        """Log the full upstream error body with the API key redacted."""
        try:
            body = response.json()
            body_text = json.dumps(body, indent=2)
        except Exception:
            body_text = response.text or "<empty body>"
        logger.error(
            "Google Maps upstream error",
            extra={
                "operation": operation,
                "status_code": response.status_code,
                "url": self._redact_url(str(response.url)),
                "upstream_body": body_text,
            },
        )

    def _log_transport_error(self, operation: str, exc: Exception) -> None:
        logger.warning(
            "Google Maps transport error",
            extra={"operation": operation, "error": type(exc).__name__},
        )

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
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            self._log_transport_error("places_autocomplete", exc)
            raise GoogleMapsError("Places autocomplete failed") from exc
        if response.status_code >= 400:
            self._log_upstream_error("places_autocomplete", response)
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
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            self._log_transport_error("place_details", exc)
            raise GoogleMapsError("Place details failed") from exc
        if response.status_code >= 400:
            self._log_upstream_error("place_details", response)
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
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(self.ROUTES_URL, json=body, headers=headers)
        except httpx.HTTPError as exc:
            self._log_transport_error("routes_api", exc)
            raise GoogleMapsError("Routes API failed") from exc
        if response.status_code >= 400:
            self._log_upstream_error("routes_api", response)
            raise GoogleMapsError(f"Routes API failed (HTTP {response.status_code})")
        return response.json()

    async def reverse_geocode(self, latitude: float, longitude: float) -> str | None:
        if not self.api_key:
            return None

        url = f"{self.BASE_URL}/geocode/json"
        params = {"latlng": f"{latitude},{longitude}", "key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            self._log_transport_error("reverse_geocode", exc)
            return None
        if response.status_code >= 400:
            self._log_upstream_error("reverse_geocode", response)
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

    async def fetch_static_map(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 15,
        width: int = 400,
        height: int = 250,
    ) -> tuple[bytes, str]:
        """Fetch a Static Maps image without exposing the server key to callers."""
        url = self.static_map_url(latitude, longitude, zoom, width, height)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            self._log_transport_error("static_map", exc)
            raise GoogleMapsError("Static map request failed") from exc

        if response.status_code >= 400:
            self._log_upstream_error("static_map", response)
            raise GoogleMapsError(
                f"Static map request failed (HTTP {response.status_code})"
            )

        content_type = response.headers.get("content-type", "image/png").split(";", 1)[0]
        if not content_type.startswith("image/"):
            logger.warning(
                "Google Static Maps returned a non-image response",
                extra={"content_type": content_type},
            )
            raise GoogleMapsError("Static map response was not an image")
        return response.content, content_type

    async def health_check(self) -> dict[str, bool]:
        """Verify the configured key can reach Routes and Places APIs.

        Returns a mapping of service -> ok. Logs warnings for any failures.
        """
        results: dict[str, bool] = {"routes": False, "places": False}
        if not self.api_key:
            logger.warning("Google Maps server key is not configured; skipping health check")
            return results

        # Routes API minimal call
        try:
            body = {
                "origins": [{"waypoint": {"location": {"latLng": {"latitude": -15.4167, "longitude": 28.2833}}}}],
                "destinations": [{"waypoint": {"location": {"latLng": {"latitude": -15.393, "longitude": 28.336}}}}],
                "travelMode": "DRIVE",
            }
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,condition",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.ROUTES_URL, json=body, headers=headers)
            if response.status_code < 400:
                results["routes"] = True
            else:
                self._log_upstream_error("health_check_routes", response)
        except Exception as exc:
            logger.warning("Routes API health check failed", extra={"error": type(exc).__name__, "error_detail": str(exc)})

        # Places API minimal call
        try:
            url = f"{self.PLACES_BASE_URL}/places:autocomplete"
            body = {
                "input": "Lusaka",
                "sessionToken": "unistay-health-check",
                "regionCode": settings.google_maps_places_region,
            }
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "suggestions.placePrediction.text",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=body, headers=headers)
            if response.status_code < 400:
                results["places"] = True
            else:
                self._log_upstream_error("health_check_places", response)
        except Exception as exc:
            logger.warning("Places API health check failed", extra={"error": type(exc).__name__, "error_detail": str(exc)})

        if not all(results.values()):
            logger.warning(
                "Google Maps health check did not pass for all services",
                extra=results,
            )
        else:
            logger.info("Google Maps health check passed", extra=results)
        return results

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
