# UniStay API

FastAPI backend for UniStay.

## Local setup

```bash
cp .env.example .env
# Edit .env and set JWT_SECRET
docker compose up --build
```

## Migrations

```bash
docker compose exec api alembic revision --autogenerate -m "description"
docker compose exec api alembic upgrade head
```

## Tests

```bash
docker compose exec api pytest
```
