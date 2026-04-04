# Production image — Python FastAPI backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Schema is applied via SQL (sql/repository_analysis_schema.sql + admin_grant_app_role.sql), not Alembic at boot.
# init_db() still honors SKIP_ALEMBIC_UPGRADE for optional local Alembic; keep it true for DML-only DB users.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
