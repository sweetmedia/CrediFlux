# syntax=docker/dockerfile:1.7
# Backend de CrediFlux. Dependencias con uv (backend/pyproject.toml + uv.lock).
FROM python:3.11-slim

# El entorno vive FUERA de /app: los compose montan ./backend sobre /app y
# taparían un /app/.venv. Con /opt/venv al frente del PATH, `python`,
# `celery`, `pytest`, `gunicorn`… resuelven al entorno sin `uv run`.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# libpq-dev + gcc: psycopg2 (no -binary) compila contra libpq.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /usr/local/bin/

# Sólo los manifiestos primero: la capa de dependencias se cachea mientras
# pyproject.toml / uv.lock no cambien. Incluye el grupo `dev` (pytest, ruff…),
# como antes requirements/development.txt.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
