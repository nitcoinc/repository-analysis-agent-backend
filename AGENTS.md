# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

This repository is the **Python FastAPI backend** at the **repo root**. The Next.js frontend is a **separate project**. **PostgreSQL is external** (e.g. Supabase via `DATABASE_URL`). Docker Compose runs **Neo4j, Redis, and the backend** from the root `docker-compose.yml`.

### Services overview

| Service | How to run | Port |
|---|---|---|
| **PostgreSQL** | Hosted (Supabase, etc.) — set `DATABASE_URL` in `.env` | (provider) |
| **Neo4j** | `sudo docker compose up -d neo4j` | 7474 (HTTP), 7687 (Bolt) |
| **Redis** | `sudo docker compose up -d redis` | 6379 |
| **Backend** | `uvicorn main:app --host 0.0.0.0 --port 8000` (from repo root) or `docker compose up -d backend` | 8000 |

### Starting all infrastructure

```bash
sudo dockerd &>/tmp/dockerd.log &
sleep 3
sudo docker compose up -d   # from repo root — requires DATABASE_URL in .env for the API
```

### Database (hosted Postgres + schema)

- Apply **`sql/repository_analysis_schema.sql`** in Supabase (or equivalent) when creating objects in schema **`repository_analysis`**.
- Set **`DATABASE_URL`** and **`POSTGRES_SCHEMA=repository_analysis`** in `.env`.
- After tables exist, run **`alembic stamp head`** once (with the same env) so `alembic upgrade head` on startup does not fail with “relation already exists”.

### Database initialization gotcha (legacy / empty DB)

Alembic history has edge cases on a totally fresh DB. If you are not using the SQL file and hit migration issues, you may still use SQLAlchemy create-all then stamp (see older docs); prefer the Supabase SQL file + `alembic stamp head` for hosted setups.

### Frontend (separate repository)

Point the frontend at this API (e.g. `NEXT_PUBLIC_API_URL=http://localhost:8000` in that project’s `.env.local`, without `/api`, if it uses Next rewrites).

### Backend notes

- **Do NOT use `--reload`** when running the backend with `uvicorn` if clones write under `./repositories/` without excludes — restarts drop in-memory analysis state.
- No test framework or linter is configured for the backend.
- Configure `.env` at the repo root (`DATABASE_URL`, `POSTGRES_SCHEMA`, Neo4j, etc.).
- `OPENAI_API_KEY` and `GITHUB_TOKEN` are optional; features degrade gracefully without them.
- The backend runs Alembic `upgrade head` on startup via `init_db()`.
- Analysis may complete with status `"paused"` when the human_review_agent creates checkpoints.

### Lint / Build / Test

- **Backend image**: `docker compose build backend` or `docker build -f Dockerfile .` from repo root.
- **Backend**: No automated tests or linter configured.
