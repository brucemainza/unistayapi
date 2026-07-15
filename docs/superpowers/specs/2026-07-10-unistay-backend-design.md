# UniStay Backend Design

> Historical design artifact. The verified current contract is maintained in `README.md` and `API_REFERENCE.md`; earlier mock-only implementation notes in this document are not production guidance.

## Status

Approved by user on 2026-07-10.

## Context

UniStay is a Flutter boarding-house discovery and landlord-management app. The existing codebase uses a single Dart library with `part of` directives, `ChangeNotifier` viewmodels, and only the Lenco payment flow is wired to a real backend today. Auth, houses, rooms, favorites, notifications, and landlord features are mocked locally.

This document designs a new, production-grade FastAPI backend that replaces the mocked data with real endpoints while preserving the response shapes the Flutter app expects.

## Goals

- Provide real endpoints for every feature currently implemented in the Flutter app.
- Maintain the `{status, message, data}` envelope the app consumes.
- Implement a clean, layered architecture with dependency injection.
- Support geospatial listing and university search via PostGIS.
- Integrate Lenco mobile-money payments with a proper state machine and webhook signature verification.
- Run locally and on a single AWS EC2 instance via Docker Compose.

## Non-goals

- No microservices, message queues, or Kubernetes.
- No features not present in the current Flutter UI (e.g., messaging, reviews, ratings, admin panel).
- No live Lenco calls without a real API key.

## Tech stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.12+) |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Auth | bcrypt + python-jose (JWT) |
| HTTP client | httpx (async) |
| Container | Docker + Docker Compose |
| Reverse proxy | nginx |
| Testing | pytest + pytest-asyncio |

## Project structure

```
UNISTAY API/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI factory and lifespan
│   ├── config.py               # pydantic-settings
│   ├── dependencies.py         # DI wiring
│   ├── exceptions.py           # typed exceptions + global handler
│   ├── logging_config.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── universities.py
│   │   ├── houses.py
│   │   ├── bookings.py
│   │   ├── payments.py
│   │   ├── notifications.py
│   │   └── landlords.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── house_service.py
│   │   ├── booking_service.py
│   │   ├── payment_service.py
│   │   ├── notification_service.py
│   │   └── lenco_client.py
│   ├── repositories/
│   │   ├── user_repo.py
│   │   ├── house_repo.py
│   │   ├── booking_repo.py
│   │   ├── payment_repo.py
│   │   └── notification_repo.py
│   ├── models/
│   │   └── all SQLAlchemy models
│   └── schemas/
│       └── Pydantic v2 request/response schemas
├── tests/
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Architecture

- **Routers** parse requests, call services, and return envelope responses.
- **Services** contain business logic and orchestrate repositories inside transactions.
- **Repositories** handle SQLAlchemy queries; one repository per aggregate.
- **Models** are SQLAlchemy 2.0 declarative tables.
- **Schemas** are Pydantic v2 models for request/response validation.
- **Dependencies** provide DB sessions and service instances via FastAPI `Depends`.

## Database schema

### Tables

| Table | Description |
|---|---|
| `users` | Platform users: students and landlords. |
| `universities` | Universities with geospatial coordinates. |
| `houses` | Landlord-owned boarding houses with geospatial coordinates. |
| `rooms` | Room types within a house. |
| `house_amenities` | Normalized amenities per house. |
| `house_images` | Image URLs for a house. |
| `nearby_universities` | Free-text nearby university names and distances for display. |
| `favorites` | Student favorite houses. |
| `bookings` | Student booking requests. |
| `payments` | Lenco payment records with state machine. |
| `notifications` | User notifications. |
| `landlord_payment_details` | Settlement account info for landlords. |
| `ad_slides` | Carousel slides for the home screen. |

### Key fields

- `users`: id, full_name, phone (unique), email, password_hash, role (`student` | `landlord`), is_verified, created_at.
- `universities`: id, name, initials, coords (`GEOGRAPHY(POINT,4326)`).
- `houses`: id, landlord_id, name, location, coords (`GEOGRAPHY(POINT,4326)`), university_id, price, walk_time, drive_distance, rating, available_spaces, accent (hex), payment_methods (JSON), created_at.
- `rooms`: id, house_id, type, rent, deposit, available, features (JSON).
- `bookings`: id, student_id, house_id, room_id, move_in_date, status, created_at, updated_at.
- `payments`: id, reference (unique), lenco_reference, booking_id, amount (numeric), currency, operator, phone, status, payload (JSON), created_at, updated_at.

### Constraints

- `favorites`: unique (`user_id`, `house_id`).
- `bookings`: use Postgres `SELECT FOR UPDATE` on `rooms` or an `EXCLUDE` constraint on date ranges to prevent double-booking.
- `houses` and `universities`: PostGIS indexes on `coords`.

## API endpoints

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/verify-otp`
- `POST /api/auth/resend-otp`
- `GET /api/auth/me`

### Users
- `GET /api/users/me`
- `PATCH /api/users/me`
- `GET /api/users/me/stats`
- `GET /api/users/me/accommodation`

### Universities
- `GET /api/universities`

### Houses
- `GET /api/houses`
- `GET /api/houses/{id}`
- `GET /api/houses/{id}/rooms`
- `GET /api/houses/{id}/similar`
- `GET /api/houses/nearby`

### Favorites
- `GET /api/favorites`
- `POST /api/favorites`
- `DELETE /api/favorites/{house_id}`

### Bookings
- `POST /api/bookings`
- `GET /api/bookings`
- `GET /api/bookings/{id}/receipt`
- `PATCH /api/bookings/{id}/status`

### Payments
- `POST /api/payments/lenco/mobile-money`
- `GET /api/payments/lenco/{reference}`
- `POST /api/webhooks/lenco`

### Notifications
- `GET /api/notifications`
- `PATCH /api/notifications/{id}/read`
- `PATCH /api/notifications/read-all`

### Landlords
- `GET /api/landlords/me/houses`
- `POST /api/landlords/houses`
- `PATCH /api/landlords/houses/{id}`
- `DELETE /api/landlords/houses/{id}`
- `POST /api/landlords/houses/{id}/rooms`
- `PATCH /api/landlords/houses/{id}/rooms/{room_id}`
- `DELETE /api/landlords/houses/{id}/rooms/{room_id}`
- `PATCH /api/landlords/houses/{id}/amenities`
- `GET /api/landlords/payment-details`
- `PUT /api/landlords/payment-details`
- `GET /api/landlords/bookings`
- `PATCH /api/landlords/bookings/{booking_id}/status`

## Request/response compatibility

All successful responses use the envelope:
```json
{ "status": true, "message": "...", "data": { ... } }
```

Errors use:
```json
{ "status": false, "message": "...", "data": null }
```

Critical compatibility notes from the Flutter app:
- Auth response shape: `{data: {user: {...}, token: "..."}}`.
- Payment response shape: `{data: {reference, status, amount, currency, lencoReference}}`.
- Payment status strings: `pay-offline`, `successful`, `failed`, `pending`, `processing`.
- `PaymentSession.amount` is a string.
- House `accent` is a hex color string.
- `nearbyUniversities` returns as `List<{name, distance}>`.
- Dev token `dev-student-token` works outside production.

## Lenco payment state machine

```
pending → processing → completed
                ├→ failed
                └→ cancelled
```

1. `POST /api/payments/lenco/mobile-money` creates a `Payment` row in `pending`.
2. It calls the Lenco collection API, then transitions to `processing`.
3. The Lenco webhook `POST /api/webhooks/lenco` verifies the signature and updates status to `completed` or `failed`.
4. `GET /api/payments/lenco/{reference}` returns the current status.
5. In mock mode (`LENCO_MOCK=true`), the service simulates Lenco responses and auto-completes after a short delay.

## Auth and security

- Password hashing with `bcrypt`.
- JWT access tokens via `python-jose`.
- Phone OTP verification with 5-digit codes stored in a short-lived DB table with an expiry timestamp.
- Mock OTP mode allows any code outside production.
- Protected routes require `Authorization: Bearer <token>`.

## Error handling and logging

- Typed exceptions: `NotFoundError`, `ConflictError`, `AuthError`, `ValidationError`, `LencoError`.
- Global exception handler converts exceptions to the envelope format.
- Structured JSON logging with request correlation IDs.
- No stack traces leaked in production.

## Docker Compose services

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: unistay
      POSTGRES_USER: unistay
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    depends_on:
      - db
    environment:
      - DATABASE_URL
      - JWT_SECRET
      - JWT_EXPIRES_IN
      - LENCO_MOCK
      - LENCO_API_KEY
      - LENCO_BASE_URL
      - LENCO_WEBHOOK_SECRET
    ports:
      - "8000:8000"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
```

## Testing

- `pytest` with `pytest-asyncio`.
- Separate test database in Docker Compose.
- Fixtures for users, houses, rooms, bookings.
- Test coverage:
  - Auth registration and login.
  - Booking double-booking prevention.
  - Lenco webhook signature verification.
  - Geospatial nearby search.
  - Favorite add/remove.

## Open questions resolved

- University table will include geospatial coordinates (`latitude`, `longitude`) for anchoring search.
- nginx will be used as a reverse proxy.
- The backend will be created at `/home/mainzabruce/Desktop/UNISTAY API/`.
