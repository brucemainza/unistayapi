# UniStay API

FastAPI backend for UniStay, a boarding-house discovery and landlord-management app.

## Tech stack

- **Framework:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL 16 + PostGIS 3.4
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Settings:** pydantic-settings
- **Auth:** bcrypt + python-jose (JWT)
- **HTTP client:** httpx
- **Container:** Docker + Docker Compose
- **Reverse proxy:** nginx
- **Testing:** pytest + pytest-asyncio

## Project structure

```
UNISTAY API/
├── alembic/              # Alembic migrations
├── app/
│   ├── main.py           # FastAPI app
│   ├── config.py         # pydantic-settings
│   ├── dependencies.py   # DI wiring
│   ├── exceptions.py     # typed exceptions
│   ├── logging_config.py # structured logging
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── repositories/     # data access layer
│   ├── services/         # business logic
│   ├── routers/          # API endpoints
│   ├── clients/          # external API clients
│   └── seed.py           # development seed data
├── tests/                # pytest suite
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── alembic.ini
├── pyproject.toml
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
| `GOOGLE_MAPS_SERVER_KEY` | Google Maps Platform server API key | optional (required in production) |
| `GOOGLE_MAPS_SIGNING_SECRET` | Google Static Maps URL signing secret | optional |
| `GOOGLE_MAPS_PLACES_REGION` | Places API region bias (ISO-3166-1 alpha-2) | `ZM` |
| `REDIS_URL` | Redis connection URL (Upstash/Redis Cloud) | optional (required in production) |
| `RESEND_API_KEY` | Resend transactional email API key | optional |
| `OTP_TTL_SECONDS` | Email OTP validity window | `600` |
| `OTP_RESEND_COOLDOWN` | Minimum seconds between OTP resends | `60` |
| `OTP_MAX_ATTEMPTS` | Maximum OTP verification attempts per code | `5` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | required for image uploads |
| `CLOUDINARY_API_KEY` | Cloudinary API key | required for image uploads |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | required for image uploads |
| `CLOUDINARY_FOLDER` | Default Cloudinary folder | `unistay` |
| `CLOUDINARY_SECURE` | Use HTTPS delivery URLs | `true` |
| `ENVIRONMENT` | `development`, `test`, or `production` | `development` |

## System overview

UniStay API is a FastAPI backend built around three layers:

- **Routers** (`app/routers/`) expose REST endpoints under `/api/*` and return a Flutter-compatible JSON envelope: `{status, message, data}`.
- **Services** (`app/services/`) contain business logic (auth, houses, bookings, payments, geo, etc.).
- **Repositories** (`app/repositories/`) handle SQLAlchemy data access.
- **Models** (`app/models/`) define PostgreSQL + PostGIS tables via SQLAlchemy 2.0.
- **Clients** (`app/clients/`) wrap external APIs: Lenco (payments), Google Maps (places/ETA/static maps), Cloudinary (images), and Resend (email OTP).

### Authentication

- Register/login returns a JWT.
- In non-production environments, the token `dev-student-token` is accepted as a convenience for testing.
- Email signup uses a 6-digit OTP stored in Redis (hashed).
- Phone OTP verification is mocked in non-production; in production it checks the `otps` table.

### External integrations

| Feature | Local/test | Production on Render |
|---|---|---|
| Payments (Lenco) | `LENCO_MOCK=true` simulates responses | Requires `LENCO_API_KEY` and `LENCO_WEBHOOK_SECRET` |
| Google Maps | Optional; endpoints error if not configured | Required: `GOOGLE_MAPS_SERVER_KEY`; optional signing secret |
| Redis | Optional for rate limiting/OTP in dev | Required: `REDIS_URL` |
| Image uploads | Optional | Required: Cloudinary credentials |
| Email OTP | Optional; skipped if no Resend key | Required: `RESEND_API_KEY` |

### Database

- PostgreSQL 16 + PostGIS 3.4 is required for geospatial queries.
- Alembic migrations live in `alembic/versions/` and run automatically in the Docker entrypoint.
- `schema.sql` / `supabase_schema.sql` are reference dumps of the full PostgreSQL schema.

## Local setup

```bash
# 1. Clone/copy the project and enter the directory
cd "UNISTAY API"

# 2. Create environment file
cp .env.example .env
# Edit .env and set a secure JWT_SECRET

# 3. Start the stack
docker compose up --build -d

# 4. Run migrations (only needed if not using the image CMD)
docker compose exec api alembic upgrade head

# 5. Seed sample data (optional)
docker compose exec api python -c "from app.dependencies import async_session; from app.seed import seed_sample_data; import asyncio; asyncio.run(seed_sample_data(next(iter(async_session()))))"

# 6. Visit the docs
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

The test suite runs inside the API container against an in-memory SQLite database:

```bash
docker compose exec api pytest
```

To run tests locally (requires Python 3.12+ and dependencies):

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## API overview

All responses use the Flutter-compatible envelope:

```json
{ "status": true, "message": "...", "data": { ... } }
```

Errors use:

```json
{ "status": false, "message": "...", "data": null }
```

### Endpoints

| Group | Endpoint | Description |
|---|---|---|
| Auth | `POST /api/auth/register` | Register a student or landlord |
| Auth | `POST /api/auth/login` | Log in with phone and password |
| Auth | `POST /api/auth/verify-otp` | Verify 5-digit OTP |
| Auth | `POST /api/auth/resend-otp` | Resend phone OTP |
| Auth | `POST /api/auth/signup` | Sign up and send email OTP (5/min/IP) |
| Auth | `POST /api/auth/verify-email` | Verify 6-digit email OTP |
| Auth | `POST /api/auth/resend-email-otp` | Resend email OTP |
| Auth | `GET /api/auth/me` | Current user profile |
| Users | `GET /api/users/me` | Profile |
| Users | `PATCH /api/users/me` | Update profile |
| Users | `GET /api/users/me/stats` | User stats |
| Universities | `GET /api/universities` | List universities |
| Houses | `GET /api/houses` | Search/list houses (supports `university_id` + `radius_m`) |
| Houses | `GET /api/houses/{id}` | House detail |
| Houses | `GET /api/houses/{id}/rooms` | House rooms |
| Houses | `GET /api/houses/{id}/similar` | Similar houses |
| Houses | `GET /api/houses/{id}/eta` | ETA from a university (cached) |
| Houses | `GET /api/houses/{id}/static-map` | Signed Google Static Maps image URL |
| Houses | `GET /api/houses/nearby` | Nearby houses (PostGIS) |
| Images | `POST /api/images/upload` | Upload a single image to Cloudinary |
| Images | `POST /api/images/upload-multiple` | Upload multiple images to Cloudinary |
| Places | `GET /api/places/autocomplete` | Google Places autocomplete proxy |
| Places | `GET /api/places/details` | Google Place details proxy |
| Favorites | `GET /api/favorites` | List favorites |
| Favorites | `POST /api/favorites` | Add favorite |
| Favorites | `DELETE /api/favorites/{house_id}` | Remove favorite |
| Bookings | `POST /api/bookings` | Create booking |
| Bookings | `GET /api/bookings` | List bookings |
| Bookings | `GET /api/bookings/{id}/receipt` | Booking receipt |
| Bookings | `PATCH /api/bookings/{id}/status` | Update booking status |
| Payments | `POST /api/payments/lenco/mobile-money` | Initiate payment |
| Payments | `GET /api/payments/lenco/{reference}` | Payment status |
| Payments | `POST /api/webhooks/lenco` | Lenco webhook |
| Notifications | `GET /api/notifications` | List notifications |
| Notifications | `PATCH /api/notifications/{id}/read` | Mark as read |
| Landlords | `GET /api/landlords/me/houses` | Landlord houses |
| Landlords | `POST /api/landlords/houses` | Create house |
| Landlords | `PATCH /api/landlords/houses/{id}` | Update house |
| Landlords | `DELETE /api/landlords/houses/{id}` | Delete house |
| Landlords | `POST /api/landlords/houses/{id}/rooms` | Add room |
| Landlords | `PATCH /api/landlords/houses/{id}/rooms/{room_id}` | Update room |
| Landlords | `DELETE /api/landlords/houses/{id}/rooms/{room_id}` | Delete room |
| Landlords | `PATCH /api/landlords/houses/{id}/amenities` | Update amenities |
| Landlords | `GET /api/landlords/payment-details` | Get payment details |
| Landlords | `PUT /api/landlords/payment-details` | Save payment details |
| Landlords | `GET /api/landlords/bookings` | Landlord bookings |
| Landlords | `PATCH /api/landlords/bookings/{id}/status` | Update booking status |

## Deployment on Render

The repository includes a `Dockerfile` that runs the API directly (no Docker Compose needed). Render builds and runs this image, so nginx and the local Postgres container from `docker-compose.yml` are not used.

### 1. Create a Web Service

1. In Render, click **New +** → **Web Service**.
2. Connect the `unistayapi` GitHub repository.
3. Select **Docker** as the runtime (Render will use the `Dockerfile`).
4. Set the service name, region, and instance type.

### 2. Create a PostgreSQL database

1. In Render, click **New +** → **PostgreSQL**.
2. Copy the **External Database URL**.
3. Note: Render Postgres does **not** include PostGIS by default. Either:
   - Use Render's managed Postgres and run `CREATE EXTENSION postgis;` manually, or
   - Provision a PostGIS-enabled Postgres elsewhere and point `DATABASE_URL` to it.

### 3. Create a Redis instance

1. Click **New +** → **Redis** (or use an external Redis provider like Upstash).
2. Copy the connection URL.

### 4. Configure environment variables

In the Web Service → **Environment** tab, add at least:

| Variable | Value / source |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Render Postgres external URL |
| `JWT_SECRET` | Generate a long random string |
| `JWT_EXPIRES_IN` | `86400` |
| `REDIS_URL` | Render Redis URL |
| `GOOGLE_MAPS_SERVER_KEY` | Your Google Maps Platform server key |
| `LENCO_MOCK` | `false` (when going live) or `true` (to keep testing) |
| `LENCO_API_KEY` | From Lenco dashboard |
| `LENCO_WEBHOOK_SECRET` | From Lenco dashboard |
| `LENCO_BASE_URL` | `https://api.lenco.co` |
| `RESEND_API_KEY` | From Resend dashboard |
| `CLOUDINARY_CLOUD_NAME` | From Cloudinary dashboard |
| `CLOUDINARY_API_KEY` | From Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | From Cloudinary dashboard |
| `CLOUDINARY_FOLDER` | `unistay` |

The `Dockerfile` entrypoint runs `alembic upgrade head` before starting uvicorn, so migrations are applied automatically on deploy.

### 5. Deploy

1. Click **Create Web Service**.
2. Render builds the image, runs migrations, and starts the API on the port it assigns via `$PORT`.
3. Once the deploy is healthy, your API is available at the Render URL (e.g. `https://unistay-api.onrender.com`).

## Testing on Render

After the deploy is live:

```bash
# 1. Health check
 curl https://your-render-url.onrender.com/api/health

# 2. OpenAPI docs
 open https://your-render-url.onrender.com/docs

# 3. Register a test user
 curl -X POST https://your-render-url.onrender.com/api/auth/register \
   -H "Content-Type: application/json" \
   -d '{"full_name":"Test Student","phone":"0977000001","email":"test@example.com","password":"secret123","role":"student"}'

# 4. Log in
 curl -X POST https://your-render-url.onrender.com/api/auth/login \
   -H "Content-Type: application/json" \
   -d '{"phone":"0977000001","password":"secret123"}'

# 5. List universities
 curl https://your-render-url.onrender.com/api/universities

# 6. List houses
 curl https://your-render-url.onrender.com/api/houses
```

### What to verify

- `/api/health` returns `status: true`.
- `/docs` loads the OpenAPI UI.
- Auth endpoints return tokens and user data.
- House/university endpoints return seeded data (seed universities are inserted automatically when the table is empty; sample houses can be seeded manually with the command in the Local setup section).
- If `LENCO_MOCK=true`, payment endpoints return mock responses without needing real Lenco credentials.

## AWS EC2 alternative

If you prefer a VM instead of Render:

1. Provision an EC2 instance and install Docker + Docker Compose.
2. Clone the repository and copy `.env.example` to `.env`.
3. Set production values: `ENVIRONMENT=production`, strong `JWT_SECRET`, real `LENCO_API_KEY` and `LENCO_WEBHOOK_SECRET`.
4. Run `docker compose up --build -d`.
5. Run migrations: `docker compose exec api alembic upgrade head`.
6. Configure your DNS to point to the EC2 instance and ensure port 80 is open.

## Development notes

- The dev token `dev-student-token` is accepted outside production for testing protected endpoints.
- In mock mode (`LENCO_MOCK=true`), Lenco mobile-money payments are simulated.
- PostGIS is required for the nearby-house search. The Docker Compose stack includes `postgis/postgis:16-3.4`.
