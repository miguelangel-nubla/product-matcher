# Build stage
FROM python:3.10-slim AS builder

WORKDIR /app/

# Install uv
COPY --from=ghcr.io/astral-sh/uv /uv /uvx /bin/

# Compile bytecode and set cache mode
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application files
COPY ./pyproject.toml ./uv.lock ./alembic.ini /app/
COPY ./app /app/app
COPY ./scripts /app/scripts

# Sync the project (production only)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Production stage
FROM python:3.10-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

# Create non-root user first
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder with correct ownership
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application files (excluding tests) with correct ownership
COPY --from=builder --chown=appuser:appuser /app/app /app/app
COPY --from=builder --chown=appuser:appuser /app/scripts /app/scripts
COPY --from=builder --chown=appuser:appuser /app/alembic.ini /app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
