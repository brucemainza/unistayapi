"""UniStay FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.clients.google_maps_client import GoogleMapsClient
from app.config import settings
from app.dependencies import async_session, close_redis, ping_redis
from app.exceptions import AppError
from app.logging_config import (
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)
from app.routers import (
    auth,
    bookings,
    favorites,
    houses,
    images,
    landlords,
    notifications,
    payments,
    places,
    universities,
    users,
)

logger = get_logger(__name__)
setup_logging(environment=settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("UniStay API starting", extra={"environment": settings.environment})
    settings.validate_for_environment(logger)
    degraded_maps = {"routes": False, "places": False}
    try:
        app.state.maps_health = await asyncio.wait_for(
            GoogleMapsClient().health_check(), timeout=25.0
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Google Maps startup health check timed out after 25s; degrading"
        )
        app.state.maps_health = degraded_maps
    except Exception as exc:
        logger.warning(
            "Google Maps startup health check raised; degrading",
            extra={"error": type(exc).__name__, "error_detail": str(exc)},
        )
        app.state.maps_health = degraded_maps
    yield
    await close_redis()
    logger.info("UniStay API shutting down")


app = FastAPI(title="UniStay API", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Return Flutter-compatible envelopes for application errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": False, "message": exc.message, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return validation errors in the Flutter-compatible envelope."""
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Validation error")
    if location:
        message = f"{location}: {message}"
    return JSONResponse(
        status_code=422,
        content={"status": False, "message": message, "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return the standard envelope for unexpected failures."""
    logger.exception(
        "Unhandled request error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "correlation_id": get_correlation_id(),
        },
    )
    return JSONResponse(
        status_code=500,
        content={"status": False, "message": "Internal server error", "data": None},
    )


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Attach a correlation id to every request and log it."""
    correlation_id = request.headers.get("x-request-id") or generate_correlation_id()
    set_correlation_id(correlation_id)

    logger.info(
        "request started",
        extra={
            "method": request.method,
            "path": request.url.path,
            "correlation_id": correlation_id,
        },
    )

    response = await call_next(request)
    response.headers["x-request-id"] = correlation_id

    logger.info(
        "request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "correlation_id": correlation_id,
        },
    )

    return response


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(universities.router, prefix="/api/universities", tags=["universities"])
app.include_router(houses.router, prefix="/api/houses", tags=["houses"])
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["favorites"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(payments.webhook_router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(places.router, prefix="/api/places", tags=["places"])
app.include_router(landlords.router, prefix="/api/landlords", tags=["landlords"])


@app.get("/api/health")
async def health_check() -> JSONResponse:
    """Return service health status."""
    maps_health = getattr(app.state, "maps_health", {"routes": False, "places": False})
    database_ok = False
    redis_ok = False

    try:
        async def check_database() -> bool:
            async with async_session() as session:
                return (await session.execute(text("select 1"))).scalar_one() == 1

        # Supabase's pooler can take several seconds to establish a fresh TLS
        # connection on a high-latency network. Keep the probe bounded, but do
        # not report a healthy database as down before a normal handshake can finish.
        database_ok = await asyncio.wait_for(check_database(), timeout=15.0)
    except Exception as exc:
        logger.warning(
            "Database health check failed",
            extra={"error": type(exc).__name__, "error_detail": str(exc)},
        )

    try:
        redis_ok = await asyncio.wait_for(ping_redis(), timeout=5.0)
    except Exception as exc:
        logger.warning(
            "Redis health check failed",
            extra={"error": type(exc).__name__, "error_detail": str(exc)},
        )

    healthy = database_ok and redis_ok and all(maps_health.values())
    body = {
        "status": healthy,
        "message": "OK" if healthy else "Service dependency unavailable",
        "data": {
            "environment": settings.environment,
            "lenco_mock": settings.lenco_mock,
            "database": database_ok,
            "redis": redis_ok,
            "google_maps": maps_health,
        },
    }
    return JSONResponse(status_code=200 if healthy else 503, content=body)
