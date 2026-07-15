# Repository Guidelines

## Project Structure & Module Organization

UniStay API is a Python 3.12 FastAPI backend. Application code lives in `app/`: `routers/` expose `/api/*` endpoints, `services/` hold business logic, `repositories/` wrap SQLAlchemy data access, `models/` define database tables, `schemas/` define Pydantic request/response shapes, and `clients/` wrap external APIs such as Google Maps, Lenco, Cloudinary, and Resend. Database migrations are in `alembic/versions/`. Tests live in `tests/`, helper scripts in `scripts/`, and API docs in `README.md` and `API_REFERENCE.md`.

## Build, Test, and Development Commands

- `pip install -e ".[dev]"` installs the package plus pytest, fakeredis, and SQLite test dependencies.
- `ENVIRONMENT=test pytest -q` runs the local test suite using in-memory SQLite and fakeredis (currently 43 passed; four PostGIS tests skip without an integration database).
- `ENVIRONMENT=test pytest tests/test_postgis_integration.py -v` runs optional PostGIS tests when `UNISTAY_INTEGRATION_DB_URL` is set.
- `docker compose up --build -d` starts the local API, Postgres/PostGIS, and related services.
- `docker compose exec api alembic upgrade head` applies migrations inside the running container.
- `docker compose exec api alembic revision --autogenerate -m "description"` creates a migration after model changes.

## Coding Style & Naming Conventions

Use 4-space indentation, type hints, and PEP 8 naming: `snake_case` for functions, variables, modules, and test files; `PascalCase` for classes and Pydantic/SQLAlchemy models. Keep routers thin, place workflow logic in services, and keep persistence concerns in repositories. Prefer async SQLAlchemy patterns already used in the codebase. No formatter or linter is currently configured in `pyproject.toml`, so keep edits consistent with nearby files.

## Testing Guidelines

Tests use `pytest` and `pytest-asyncio`; async mode is configured in `pyproject.toml`. Name tests `test_*.py` and test functions `test_*`. Add focused tests for new endpoints, service behavior, repository queries, and regression fixes. Keep the default suite independent of live services; use fakeredis, SQLite fixtures, and mocked external integrations unless a test belongs in `test_postgis_integration.py`.

## Commit & Pull Request Guidelines

Recent history mostly follows Conventional Commits, for example `fix(geo): ...`, `test(postgis): ...`, `docs(api-reference): ...`, and `build(docker): ...`. Use a short imperative subject with a scope when helpful. Pull requests should include a summary, test results, linked issue or context, migration notes for schema changes, and API/request-response examples when endpoint behavior changes.

## Security & Configuration Tips

Copy `.env.example` to `.env` for local setup and never commit secrets. Production requires strong values for `JWT_SECRET`, `DATABASE_URL`, Redis, Maps, Resend, Cloudinary, and Lenco credentials. Keep `LENCO_MOCK=false` for production verification; use Lenco sandbox/test credentials before initiating payment sweeps. Document any new environment variable in both `.env.example` and `README.md`.
