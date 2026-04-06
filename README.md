# Codebase Analysis Agent - Backend

FastAPI backend for the codebase analysis agent system. The UI lives in a **separate frontend repository**. **PostgreSQL, Neo4j, and Redis are configured via `.env`** (external endpoints). Docker Compose runs **only the API** container.

## Prerequisites

- Docker and Docker Compose v2 (optional; for running the API in a container)
- Reachable **PostgreSQL**, **Neo4j (Bolt)**, and **Redis** — URLs/hosts in `.env` (see **`.env.example`**)
- Python 3.11+ (for local runs without Docker)

## Supabase / hosted Postgres

1. Create the schema and tables in the Supabase SQL editor using **`sql/repository_analysis_schema.sql`** (or equivalent DDL in schema `repository_analysis`).

2. Copy `.env.example` to `.env` and set:
   - **`DATABASE_URL`** — from Supabase (often include `?sslmode=require`).
   - **`POSTGRES_SCHEMA=repository_analysis`** — must match the schema where tables live.
   - **`NEO4J_URI`**, **`NEO4J_USER`**, **`NEO4J_PASSWORD`**
   - **`REDIS_HOST`** / **`REDIS_PORT`** (or **`REDIS_URL`**)
   - **`SKIP_WAIT_FOR_DEPS=true`** when using Compose (no bundled DB graph)
   - **`API_KEY`**, **`SECRET_KEY`**, etc.

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

3. Health: http://localhost:8000/health — dependency probe: http://localhost:8000/health/dependencies (503 if any of Postgres/Neo4j/Redis fail) — Swagger: http://localhost:8000/docs

On startup, logs include **`[startup-check]`** lines for each dependency (OK or FAILED with stack trace).

### Compose layout

- **Build context** is the **repository root** (same directory as `Dockerfile`).
- **Volumes** persist cloned repositories and uploads only.

### Frontend (separate project)

Point the frontend at this API (e.g. `NEXT_PUBLIC_API_URL=http://localhost:8000` in that project’s `.env.local`).

## Local development (Python on the host)

1. `pip install -r requirements.txt`

2. `.env` with external **`DATABASE_URL`**, **`NEO4J_URI`**, **`REDIS_HOST`** / **`REDIS_URL`**, etc. (see `.env.example`).

3. Optional: **`SKIP_STARTUP_DEPENDENCY_CHECK=true`** only if you need the process to boot without reachable deps (not recommended).

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

## Dokploy (Dockerfile build type)

Per [Dokploy build types](https://docs.dokploy.com/docs/core/applications/build-type), set **Dockerfile path** and **context** (usually `.`). In the app **Domains** UI, set the **container port to `8000`** (not 3000).

**Why startup can fail:** `backend/wait-for-services.sh` waits for TCP on hostnames **`postgres`**, **`neo4j`**, and **`redis`**. Those names only resolve on Docker Compose’s internal network. A single Dokploy app has no such services unless you add them and join networks.

**Fix:** In Dokploy **Environment**, set **`SKIP_WAIT_FOR_DEPS=true`** (or `1`). Then set **`DATABASE_URL`**, **`NEO4J_URI`**, **`NEO4J_USER`**, **`NEO4J_PASSWORD`**, and **`REDIS_URL`** or **`REDIS_HOST`** / **`REDIS_PORT`** / **`REDIS_PASSWORD`**. For a pre-provisioned Postgres user without DDL rights, keep **`SKIP_ALEMBIC_UPGRADE=true`**.

Dokploy can inject a generated `.env` at runtime ([variables](https://docs.dokploy.com/docs/core/variables)); ensure every variable your `Settings` class needs is defined there.

## Environment variables

See `.env.example`. Compose loads `.env` for substitution; the backend container uses `env_file: .env`.
