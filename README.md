# UniStay API

FastAPI backend for UniStay, a boarding-house discovery and landlord-management app.

Current status: the full automated test suite is green, with 36 tests passing and 1 skipped. A GitHub Actions CI workflow runs the suite on every push to `dev` and `main`.

## Tech stack

- **Framework:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL 16 + PostGIS 3.4 (Supabase in production, local via Docker)
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic (auto-ran at container start)
- **Validation:** Pydantic v2
- **Settings:** pydantic-settings
- **Auth:** bcrypt + python-jose (JWT)
- **HTTP client:** httpx
- **Container:** Docker + Docker Compose (local); Docker-only on Render
- **Reverse proxy:** nginx (local only; Render handles routing natively)
- **Testing:** pytest + pytest-asyncio + GitHub Actions CI
- **Email:** Resend (transactional OTP emails)

## Current system highlights

- Startup health checks probe Google Routes API and Google Places API with a 5-second timeout. On failure the app degrades gracefully (flags set to `false`) and boots normally — a flaky Google Maps account never blocks the deploy.
- Cloudinary image uploads are working against the configured account and support both single and multiple file uploads.
- Landlord house deletion is implemented as a soft delete and hidden from public search/list/detail flows.
- External API failures are logged server-side with upstream details while the client receives a clean application error.
- The initial Alembic migration runs `CREATE EXTENSION IF NOT EXISTS postgis` ensuring fresh Supabase projects are ready without manual SQL.
- CI runs the test suite on GitHub Actions for every push and PR.

## Project structure

```
UNISTAY API/
├── .github/workflows/ci.yml   # CI pipeline
├── alembic/                   # Alembic migrations
├── app/
│   ├── main.py                # FastAPI app
│   ├── config.py              # pydantic-settings
│   ├── dependencies.py        # DI wiring
│   ├── exceptions.py          # typed exceptions
│   ├── logging_config.py      # structured logging
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── repositories/          # data access layer
│   ├── services/              # business logic
│   ├── routers/               # API endpoints
│   ├── clients/               # external API clients
│   └── seed.py                # development seed data
├── tests/                     # pytest suite + PostGIS integration tests
├── scripts/
│   ├── capture_api_responses.py  # capture responses (local + remote)
│   └── render_deploy_check.py    # smoke-test any Render deploy
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── alembic.ini
├── pyproject.toml
├── API_REFERENCE.md           # mobile-facing endpoint reference
└── .env.example
```

## Environment variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy async PostgreSQL URL | `postgresql+asyncpg://unistay:unistay@db:5432/unistay` |
| `POSTGRES_DB` | PostgreSQL database name | `unistay` |
| `POSTGRES_USER` | PostgreSQL user | `unistay` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `unistay` |
| `JWT_SECRET` | Secret key for JWT signing | **required** |
| `JWT_EXPIRES_IN` | JWT expiry in seconds | `86400` |
| `LENCO_MOCK` | Run Lenco payments in mock mode | `true` |
| `LENCO_API_KEY` | Lenco API key (production) | optional |
| `LENCO_BASE_URL` | Lenco API base URL | `https://api.lenco.co` |
| `LENCO_WEBHOOK_SECRET` | Lenco webhook secret (production) | optional |
| `GOOGLE_MAPS_SERVER_KEY` | Google Maps Platform server API key | required in production |
| `GOOGLE_MAPS_SIGNING_SECRET` | Google Static Maps URL signing secret | optional |
| `GOOGLE_MAPS_PLACES_REGION` | Places API region bias (ISO-3166-1 alpha-2) | `ZM` |
| `REDIS_URL` | Redis connection URL | required in production |
| `RESEND_API_KEY` | Resend transactional email API key | optional |
| `OTP_TTL_SECONDS` | Email OTP validity window | `600` |
| `OTP_RESEND_COOLDOWN` | Minimum seconds between OTP resends | `60` |
| `OTP_MAX_ATTEMPTS` | Maximum OTP verification attempts per code | `5` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | required for image uploads |
| `CLOUDINARY_API_KEY` | Cloudinary API key | required for image uploads |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | required for image uploads |
| `CLOUDINARY_FOLDER` | Default Cloudinary folder used for uploads | `unistay` |
| `CLOUDINARY_SECURE` | Use HTTPS delivery URLs | `true` |
| `ENVIRONMENT` | `development`, `test`, or `production` | `development` |

## System overview

UniStay API is a FastAPI backend built around three layers:

- **Routers** (`app/routers/`) expose REST endpoints under `/api/*` and return a Flutter-compatible JSON envelope: `{status, message, data}`.
- **Services** (`app/services/`) contain business logic (auth, houses, bookings, payments, geo, etc.).
- **Repositories** (`app/repositories/`) handle SQLAlchemy data access.
- **Models** (`app/models/`) define PostgreSQL + PostGIS tables via SQLAlchemy 2.0.
- **Clients** (`app/clients/`) wrap external APIs: Lenco (payments), Google Maps (places/ETA/static maps), Cloudinary (images), and Resend (email OTP).

### Validation and startup behavior

- The app probes Google Maps at startup with a 5-second timeout. If Google Maps is unreachable the app still boots and `/api/health` reports `google_maps: {routes: false, places: false}`.
- `/api/health` returns that snapshot so deploys confirm access immediately.
- Cloudinary uploads require all three credentials and use the configured folder from `CLOUDINARY_FOLDER`.

### Authentication

- Register/login returns a JWT.
- In non-production environments, the token `dev-student-token` is accepted as a convenience for testing.
- **Phone-OTP path:** `register` → (optional) 5-digit `/verify-otp` (mocked in non-prod, table-backed in prod).
- **Email-OTP path:** `signup` → 6-digit email OTP stored in Redis (hashed, 5-retry max, 60s cooldown, 10-min TTL) → `/verify-email`.

### External integrations

| Feature | Local/test | Production on Render |
|---|---|---|
| Payments (Lenco) | `LENCO_MOCK=true` simulates responses | Requires `LENCO_API_KEY` and `LENCO_WEBHOOK_SECRET` |
| Google Maps | Optional; endpoints error if not configured | Required: `GOOGLE_MAPS_SERVER_KEY`; optional signing secret |
| Redis | Optional for rate limiting/OTP in dev | Required: `REDIS_URL` (Upstash) |
| Image uploads | Optional | Required: Cloudinary credentials |
| Email OTP | Optional; skipped if no Resend key | Required: `RESEND_API_KEY` |

### Database

- PostgreSQL 16 + PostGIS 3.4 is required for geospatial queries.
- Alembic migrations live in `alembic/versions/` and run automatically in the Docker entrypoint.
- The initial migration runs `CREATE EXTENSION IF NOT EXISTS postgis` — Supabase or any PostGIS-enabled host is ready without manual SQL.
- `schema.sql` / `supabase_schema.sql` are reference dumps of the full PostgreSQL schema.

## Local setup

```bash
# 1. Clone the project and enter the directory
cd "UNISTAY API"

# 2. Create environment file
cp .env.example .env
# Edit .env and set a secure JWT_SECRET

# 3. Start the stack
docker compose up --build -d
# The API entrypoint runs alembic upgrade head automatically, then starts uvicorn.

# 4. Seed sample data (optional)
docker compose exec api python -c "
import asyncio
from app.dependencies import async_session
from app.seed import seed_sample_data

async def main():
    async with async_session() as session:
        await seed_sample_data(session)

asyncio.run(main())
"

# 5. Visit the docs
curl http://localhost/api/health
# OpenAPI docs: http://localhost/docs
```

## Migrations

Generate a new migration from model changes:

```bash
docker compose exec api alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
docker compose exec api alembic upgrade head
```

## Tests

### Local test suite (SQLite + fakeredis)

```bash
# Inside a venv with dev deps installed
pip install -e ".[dev]"
ENVIRONMENT=test pytest
```

The test suite uses an in-memory SQLite database and `fakeredis`. **36 tests pass, 1 skipped.**

### PostGIS integration tests (optional)

```bash
# Requires a live Postgres + PostGIS database (e.g., Supabase staging)
export UNISTAY_INTEGRATION_DB_URL="postgresql+asyncpg://..."
ENVIRONMENT=test pytest tests/test_postgis_integration.py -v
```

Set `UNISTAY_INTEGRATION_DB_URL` to a live Postgres+PostGIS database (e.g., a Supabase staging project). Without the variable the integration tests are skipped.

### CI (GitHub Actions)

A `.github/workflows/ci.yml` runs on every push and PR to `dev` and `main`. The default SQLite suite runs in seconds. If the repository secret `SUPABASE_TEST_DB_URL` is configured, the PostGIS integration suite also runs automatically.

## API overview

All responses use the Flutter-compatible envelope:

```json
{ "status": true, "message": "...", "data": { ... } }
```

Errors use:

```json
{ "status": false, "message": "...", "data": null }
```

### Full endpoint reference

See **[API_REFERENCE.md](API_REFERENCE.md)** — this is the mobile-facing reference with every endpoint catalogued, request/response shapes, auth requirements, casing conventions, nullable fields, rate limits, error messages, and a one-page mobile integration checklist.

### Quick endpoint list

| Group | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/verify-otp`, `POST /api/auth/resend-otp`, `POST /api/auth/signup`, `POST /api/auth/verify-email`, `POST /api/auth/resend-email-otp` |
| Users | `GET /api/users/me`, `PATCH /api/users/me`, `GET /api/users/me/stats` |
| Universities | `GET /api/universities` |
| Houses | `GET /api/houses` (list + geospatial search), `GET /api/houses/{id}`, `GET /api/houses/{id}/rooms`, `GET /api/houses/{id}/similar`, `GET /api/houses/{id}/eta`, `GET /api/houses/{id}/static-map`, `GET /api/houses/nearby` |
| Images | `POST /api/images/upload`, `POST /api/images/upload-multiple` |
| Places | `GET /api/places/autocomplete`, `GET /api/places/details` |
| Favorites | `GET /api/favorites`, `POST /api/favorites`, `DELETE /api/favorites/{house_id}` |
| Bookings | `POST /api/bookings`, `GET /api/bookings`, `GET /api/bookings/{id}/receipt`, `PATCH /api/bookings/{id}/status` |
| Payments | `POST /api/payments/lenco/mobile-money`, `POST /api/payments/lenco/card`, `GET /api/payments/lenco/{reference}`, `POST /api/webhooks/lenco` |
| Notifications | `GET /api/notifications`, `PATCH /api/notifications/{id}/read`, `PATCH /api/notifications/read-all` |
| Landlords | `GET /api/landlords/me/houses`, `POST|PATCH|DELETE /api/landlords/houses`, `POST|PATCH|DELETE /api/landlords/houses/{id}/rooms`, `PATCH /api/landlords/houses/{id}/amenities`, `PUT|GET /api/landlords/payment-details`, `GET /api/landlords/bookings` |

## Deployment on Render

### Prerequisites

You need three external services provisioned before deploying the Render web service:

1. **Supabase** — Postgres 16 + PostGIS 3.4 (bundled, no manual SQL). Free tier works.
2. **Upstash Redis** — Free tier. `rediss://default:<token>@<region>.upstash.io:6379`.
3. **Google Maps Platform** — API key with Routes API and Places API (New) enabled + linked billing account. Optional for testing.
4. **Cloudinary** — All three credentials for image uploads.

### Step-by-step Render deploy

#### 1. Create the Supabase project

1. Go to [supabase.com](https://supabase.com) → **New Project** → pick a region, set a DB password. Postgres ≥ 16 is automatically selected.
2. Once created, go to **Project Settings → Database → Connection string → URI**. Copy the **Session pooler** URL.
3. Replace `[YOUR-PASSWORD]` with the password you set during project creation.
4. Reformat the URL for SQLAlchemy async:
   ```
   postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
   (Use port `6543` — the transaction-mode pooler supports asyncpg. Port `5432` is for direct connections which also work but bypass the pooler.)
5. This URL becomes your `DATABASE_URL` env var on Render.

#### 2. Create the Upstash Redis instance

1. Go to [upstash.com](https://upstash.com) → **Create Database** → pick a region → **Create**.
2. In **Details → Connect to your database** switch to the **Upstash Redis** tab (not the REST API one).
3. Copy the whole `rediss://default:<token>@<region>.upstash.io:6379` line.
4. This becomes your `REDIS_URL` env var on Render.

#### 3. Create the Render Web Service

1. Render Dashboard → **New +** → **Web Service**.
2. Connect the `unistayapi` GitHub repository → branch `dev`.
3. Set the runtime: **Docker** (Render reads the `Dockerfile` in the repo root).
4. Choose a service name, region, and instance type (Free is fine for initial testing; Free sleeps after 15 min idle).
5. **Health Check Path:** `/api/health` (so Render can confirm the service is alive after boot).

#### 4. Configure environment variables

In the Web Service → **Environment** tab, add:

| Variable                  | Value                                    |
|---------------------------|------------------------------------------|
| `ENVIRONMENT`             | `production`                             |
| `DATABASE_URL`            | Supabase session-pooler URI (from step 1) |
| `JWT_SECRET`              | Generate a long random string (e.g. `openssl rand -hex 32`) |
| `JWT_EXPIRES_IN`          | `86400`                                  |
| `REDIS_URL`               | Upstash `rediss://...` URL (from step 2) |
| `LENCO_MOCK`              | `true` (safe default)                    |
| `LENCO_API_KEY`           | (leave blank until going live)           |
| `LENCO_WEBHOOK_SECRET`    | (leave blank until going live)           |
| `LENCO_BASE_URL`          | `https://api.lenco.co`                   |
| `GOOGLE_MAPS_SERVER_KEY`  | Your Google Maps Platform server key     |
| `GOOGLE_MAPS_PLACES_REGION`| `ZM`                                    |
| `GOOGLE_MAPS_SIGNING_SECRET`| Set if using static map URL signing (optional) |
| `RESEND_API_KEY`          | From Resend dashboard (optional; email silently skipped if missing) |
| `CLOUDINARY_CLOUD_NAME`   | From Cloudinary dashboard                |
| `CLOUDINARY_API_KEY`      | From Cloudinary dashboard                |
| `CLOUDINARY_API_SECRET`   | From Cloudinary dashboard                |
| `CLOUDINARY_FOLDER`       | `unistay`                                |

#### 5. First deploy

1. Click **Create Web Service**. Render builds the Docker image (~2-4 min), runs `alembic upgrade head` (which self-enables PostGIS), then starts uvicorn on `$PORT`.
2. Watch the Render logs for:
   - `INFO - Alembic upgrade complete` (or similar — migration success)
   - `INFO - UniStay API starting`
   - `Uvicorn running on http://0.0.0.0:<PORT>`
3. Render runs a health check against `/api/health`. If it succeeds your service is live.

#### 6. Smoke test

```bash
# Quick check from your terminal
python scripts/render_deploy_check.py https://unistay-api.onrender.com
```

Or manually:

```bash
BASE=https://unistay-api.onrender.com

# 1. Health
curl -s "$BASE/api/health" | jq .

# 2. Register a student
curl -s -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test","phone":"0977000001","email":"t@example.com","password":"secret123","role":"student"}' | jq .

# 3. Universities
curl -s "$BASE/api/universities" | jq .

# 4. Houses
curl -s "$BASE/api/houses" | jq .

# 5. Places (queries Google Maps)
curl -s "$BASE/api/places/autocomplete?input=Lusaka&session_token=smoke1" | jq .
```

### Render Free tier note

On the Free tier the container sleeps after ~15 minutes of inactivity. The first request wakes it (30-60s cold start). The mobile app should handle this with a loading state and a 60s timeout.

To keep the service always-on, upgrade to a Render Starter plan ($7/mo).

## CI (GitHub Actions)

The workflow at `.github/workflows/ci.yml` runs on every push and PR to `dev` or `main`:

1. **`test` job** — Installs `.[dev]`, runs `pytest -q` against SQLite + fakeredis. ~30s.
2. **`integration` job** — (Optional, gated on `SUPABASE_TEST_DB_URL` secret). Runs the PostGIS integration suite against a live Supabase database.

To enable PostGIS CI tests, add a repository secret `SUPABASE_TEST_DB_URL` with a staging/isolated Supabase connection string.

## AWS EC2 alternative

If you prefer a VM instead of Render:

1. Provision an EC2 instance and install Docker + Docker Compose.
2. Clone the repository and copy `.env.example` to `.env`.
3. Set production values: `ENVIRONMENT=production`, strong `JWT_SECRET`, real `LENCO_API_KEY` and `LENCO_WEBHOOK_SECRET`.
4. Run `docker compose up --build -d`.
5. Migrations run automatically at container start (`alembic upgrade head`).
6. Configure your DNS to point to the EC2 instance and ensure port 80 is open.

## Development notes

- The dev token `dev-student-token` is accepted outside production for testing protected endpoints.
- In mock mode (`LENCO_MOCK=true`), Lenco mobile-money and card payments are simulated.
- PostGIS is required for the nearby-house search and university-radius queries. The Docker Compose stack includes `postgis/postgis:16-3.4`. On Supabase it's pre-enabled.
- Google Maps, Cloudinary, and Lenco integration failures are logged server-side with useful upstream detail while the API returns clean envelopes.
- The current quick health signal is the full test suite: `pytest` should finish with 36 passed and 1 skipped.
- CI on GitHub Actions validates every push.