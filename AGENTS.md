# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

This repository is the **Python FastAPI backend** at the **repo root**. The Next.js frontend is a **separate project**. **PostgreSQL, Neo4j, and Redis are external** — configure hosts/URLs in `.env` (see `.env.example`). Docker Compose runs **only the backend** service.

### Services overview

| Service | Configuration | Notes |
|---|---|---|
| **PostgreSQL** | `DATABASE_URL` or `POSTGRES_*` in `.env` | Optional `POSTGRES_SCHEMA` |
| **Neo4j** | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Bolt |
| **Redis** | `REDIS_URL` or `REDIS_HOST` + `REDIS_PORT` (+ `REDIS_PASSWORD`) | Rate limiting + cache |
| **Backend** | `uvicorn main:app` or `docker compose up -d backend` | Port **8000** |

### Starting the API (Docker)

```bash
sudo docker compose up -d --build   # from repo root; .env must list all external endpoints
```

Set **`SKIP_WAIT_FOR_DEPS=true`** in `.env` so the container does not wait for non-existent `postgres`/`neo4j`/`redis` hostnames.

### Database (hosted Postgres + schema)

- Apply **`sql/repository_analysis_schema.sql`** when using schema **`repository_analysis`**.
- Set **`DATABASE_URL`** and **`POSTGRES_SCHEMA`** in `.env`.
- **`SKIP_ALEMBIC_UPGRADE=true`** when the DB user must not run DDL.
- Optional: **`alembic stamp head`** once so `alembic upgrade head` in Docker is a no-op.

### Observability

- Startup logs: **`[startup-check] PostgreSQL|Neo4j|Redis: OK`** or **`FAILED`** with exception.
- HTTP: **`GET /health/dependencies`** — 200 if all three are up, **503** with per-service `detail` if any fail.

### Frontend (separate repository)

Point the frontend at this API (e.g. `NEXT_PUBLIC_API_URL=http://localhost:8000` in that project’s `.env.local`, without `/api`, if it uses Next rewrites).

### Backend notes

- **Do NOT use `--reload`** when running the backend with `uvicorn` if clones write under `./repositories/` without excludes — restarts drop in-memory analysis state.
- No test framework or linter is configured for the backend.
- Configure `.env` at the repo root for all external services.
- `OPENAI_API_KEY` and `GITHUB_TOKEN` are optional; features degrade gracefully without them.
- Alembic `upgrade head` runs in Docker before Uvicorn unless **`SKIP_ALEMBIC_UPGRADE`** is set; `init_db()` mirrors this on startup.
- Analysis may complete with status `"paused"` when the human_review_agent creates checkpoints.

### Lint / Build / Test

- **Backend image**: `docker compose build backend` or `docker build -f Dockerfile .` from repo root.
- **Backend**: No automated tests or linter configured.
