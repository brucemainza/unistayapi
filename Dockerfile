FROM python:3.12-slim-bookworm

WORKDIR /app

# asyncpg ships wheels and does not require libpq-dev; omitting system packages
# keeps the image small and avoids build-time network dependencies.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir -e ".[dev]"

COPY alembic ./alembic
COPY tests ./tests
COPY alembic.ini ./

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
