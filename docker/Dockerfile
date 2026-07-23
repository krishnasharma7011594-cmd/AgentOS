FROM python:3.11-slim as base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .env.example ./
RUN pip install --upgrade pip \
    && pip install fastapi uvicorn pydantic pydantic-settings structlog typer

COPY core/ ./core/
COPY supervisor/ ./supervisor/
COPY registry/ ./registry/
COPY agents/ ./agents/
COPY workflow/ ./workflow/
COPY task_queue/ ./task_queue/
COPY knowledge/ ./knowledge/
COPY observability/ ./observability/
COPY evaluation/ ./evaluation/
COPY apps/ ./apps/

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
