"""
Startup validation for external PostgreSQL, Neo4j, and Redis.
Logs a clear [startup-check] line per service; raises if any required check fails
(unless skip_startup_dependency_check is set).
"""
import logging
import re
from urllib.parse import urlparse

from sqlalchemy import text

from core.config import get_settings
from core.database import engine, get_neo4j_driver, get_redis_client

logger = logging.getLogger(__name__)


def _postgres_log_label() -> str:
    s = get_settings()
    raw = (s.database_url or s.postgres_url or "").strip()
    if raw:
        try:
            u = urlparse(raw.replace("postgresql+psycopg2://", "postgresql://", 1))
            host = u.hostname or "?"
            port = u.port or 5432
            db = (u.path or "/").lstrip("/") or "?"
            return f"host={host} port={port} db={db}"
        except Exception:
            return "DATABASE_URL/POSTGRES_URL (configured)"
    if (s.postgres_host or "").strip():
        return f"host={s.postgres_host} port={s.postgres_port} db={s.postgres_db}"
    return "not configured"


def _redis_log_label() -> str:
    s = get_settings()
    if (s.redis_url or "").strip():
        try:
            u = urlparse(s.redis_url.replace("rediss://", "redis://", 1))
            host = u.hostname or "?"
            port = u.port or 6379
            return f"url host={host} port={port}"
        except Exception:
            return "REDIS_URL (configured)"
    return f"host={s.redis_host} port={s.redis_port} db={s.redis_db}"


def validate_external_dependencies() -> None:
    """
    Verify Postgres, Neo4j, and Redis using the same clients as the app.
    """
    settings = get_settings()
    if settings.skip_startup_dependency_check:
        logger.info("[startup-check] Skipped (SKIP_STARTUP_DEPENDENCY_CHECK is set)")
        return

    failures: list[str] = []

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[startup-check] PostgreSQL: OK (%s)", _postgres_log_label())
    except Exception as e:
        logger.error(
            "[startup-check] PostgreSQL: FAILED — %s",
            e,
            exc_info=True,
        )
        failures.append("postgresql")

    try:
        get_neo4j_driver()
        neo4j_safe = re.sub(r":([^@/]+)@", r":***@", settings.neo4j_uri or "")
        logger.info("[startup-check] Neo4j: OK (uri=%s)", neo4j_safe or "(empty)")
    except Exception as e:
        logger.error(
            "[startup-check] Neo4j: FAILED — %s",
            e,
            exc_info=True,
        )
        failures.append("neo4j")

    try:
        get_redis_client()
        logger.info("[startup-check] Redis: OK (%s)", _redis_log_label())
    except Exception as e:
        logger.error(
            "[startup-check] Redis: FAILED — %s",
            e,
            exc_info=True,
        )
        failures.append("redis")

    if failures:
        msg = (
            "Startup dependency check failed for: "
            + ", ".join(failures)
            + ". Fix .env (see .env.example) and ensure each service is reachable."
        )
        logger.error("[startup-check] %s", msg)
        raise RuntimeError(msg)


def dependency_status() -> dict:
    """
    Non-throwing snapshot for GET /health/dependencies.
    Values: {"status": "ok"} or {"status": "error", "detail": "..."}.
    """
    status: dict = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgresql"] = {"status": "ok"}
    except Exception as e:
        status["postgresql"] = {"status": "error", "detail": str(e)[:800]}

    try:
        drv = get_neo4j_driver()
        with drv.session() as session:
            session.run("RETURN 1")
        status["neo4j"] = {"status": "ok"}
    except Exception as e:
        status["neo4j"] = {"status": "error", "detail": str(e)[:800]}

    try:
        r = get_redis_client()
        r.ping()
        status["redis"] = {"status": "ok"}
    except Exception as e:
        status["redis"] = {"status": "error", "detail": str(e)[:800]}

    return status
