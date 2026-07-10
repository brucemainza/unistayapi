"""UniStay FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
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
    landlords,
    notifications,
    payments,
    universities,
    users,
)

logger = get_logger(__name__)
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("UniStay API starting", extra={"environment": settings.environment})
    yield
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
app.include_router(favorites.router, prefix="/api/favorites", tags=["favorites"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(payments.webhook_router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(landlords.router, prefix="/api/landlords", tags=["landlords"])


@app.get("/api/health")
async def health_check() -> dict:
    """Return service health status."""
    return {
        "status": True,
        "message": "OK",
        "data": {
            "environment": settings.environment,
            "lenco_mock": settings.lenco_mock,
        },
    }
