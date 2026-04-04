# Codebase Analysis Agent - Backend

FastAPI backend for the codebase analysis agent system. The UI lives in a **separate frontend repository**. **PostgreSQL is hosted externally** (e.g. Supabase). Docker Compose runs **Neo4j, Redis, and the API** only.

## Prerequisites

- Docker and Docker Compose v2
- A **PostgreSQL** database (connection string in `.env` as `DATABASE_URL`)
- Python 3.11+ (for local runs without Docker)

## Supabase / hosted Postgres

1. Create the schema and tables in the Supabase SQL editor using **`sql/repository_analysis_schema.sql`** (or equivalent DDL in schema `repository_analysis`).

2. Copy `.env.example` to `.env` and set:
   - **`DATABASE_URL`** — from Supabase (often include `?sslmode=require`).
   - **`POSTGRES_SCHEMA=repository_analysis`** — must match the schema where tables live.
   - **`NEO4J_PASSWORD`**, **`API_KEY`**, **`SECRET_KEY`**, etc.

3. **Stamp Alembic** once so startup migrations do not try to recreate existing tables:

```bash
export DATABASE_URL="your-connection-string"
export POSTGRES_SCHEMA=repository_analysis
alembic stamp head
```

4. Start the stack:

```bash
docker compose up -d --build
```

5. Open http://localhost:8000/docs and call the API with header **`X-API-Key`** matching `API_KEY`.

The Docker image runs `alembic upgrade head` before Uvicorn; after `stamp head`, that step is a no-op until new migrations exist.

### If you use `public` only

Leave **`POSTGRES_SCHEMA`** empty and either run Alembic migrations against an empty DB, or create tables in `public` and still run `alembic stamp head` when the schema already matches the migration chain.

## Quick start (Docker)

1. `cp .env.example .env` and fill **`DATABASE_URL`**, **`POSTGRES_SCHEMA`** (if using `repository_analysis`), **Neo4j** and **backend** secrets.

2. `docker compose up -d --build`

3. Health: http://localhost:8000/health — Swagger: http://localhost:8000/docs

### Compose layout

- **Build context** is the **repository root** (same directory as `Dockerfile`).
- **Volumes** persist cloned repositories, uploads, Neo4j, and Redis data — not Postgres.

### Frontend (separate project)

Point the frontend at this API (e.g. `NEXT_PUBLIC_API_URL=http://localhost:8000` in that project’s `.env.local`).

## Local development (Python on the host)

1. `pip install -r requirements.txt`

2. Start Neo4j and Redis only:

```bash
docker compose up -d redis neo4j
```

3. `.env` with **`DATABASE_URL`** (Supabase or local Postgres) and optional **`POSTGRES_SCHEMA`**.

4. `alembic upgrade head` (or `alembic stamp head` if tables already exist).

5. Run the API:

```bash
python main.py
```

Or with reload excludes:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 \
  --reload-exclude ./repositories --reload-exclude ./uploads
```

See `AGENTS.md` for reload caveats.

## Production-oriented notes

- Keep `.env` out of version control; inject variables via your platform.
- Do not expose Redis or Neo4j on the public internet; only publish the API (or a reverse proxy) on `80`/`443`.
- See `.env.example` for variables.

## Environment variables

See `.env.example`. Compose loads `.env` for substitution; the backend container uses `env_file: .env`.
