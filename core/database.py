import logging
from typing import Optional
from neo4j import GraphDatabase
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from redis import Redis

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Base = declarative_base()

# Resolved once per process (SQLAlchemy engine + Alembic both call resolve_postgres_url).
_resolved_postgres_url: Optional[str] = None


def resolve_postgres_url() -> str:
    """DSN for SQLAlchemy and Alembic: DATABASE_URL first, else POSTGRES_URL, else POSTGRES_* components."""
    global _resolved_postgres_url
    if _resolved_postgres_url is not None:
        return _resolved_postgres_url

    primary = (settings.database_url or "").strip()
    if primary:
        print("Using DATABASE_URL for DB connection", flush=True)
        _resolved_postgres_url = primary
        return primary

    legacy_url = (settings.postgres_url or "").strip()
    if legacy_url:
        print("Using POSTGRES_URL for DB connection", flush=True)
        _resolved_postgres_url = legacy_url
        return legacy_url

    host = (settings.postgres_host or "").strip()
    user = (settings.postgres_user or "").strip()
    db = (settings.postgres_db or "").strip()
    password = settings.postgres_password or ""
    port = settings.postgres_port

    if not host or not user or not db:
        raise ValueError(
            "Database configuration missing. Set DATABASE_URL or POSTGRES_* variables."
        )

    print("Using individual POSTGRES_* configuration for DB connection", flush=True)
    built = (
        f"postgresql://{user}:{password}"
        f"@{host}:{port}/{db}"
    )
    _resolved_postgres_url = built
    return built


def _postgres_connect_args() -> dict:
    schema = (settings.postgres_schema or "").strip()
    if not schema:
        return {}
    return {"options": f"-c search_path={schema},public"}


# Neo4j Connection
_neo4j_driver: Optional[GraphDatabase.driver] = None


def get_neo4j_driver():
    """Get or create Neo4j driver instance."""
    global _neo4j_driver
    if _neo4j_driver is None:
        try:
            _neo4j_driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            # Test connection
            with _neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    return _neo4j_driver


def close_neo4j_driver():
    """Close Neo4j driver connection."""
    global _neo4j_driver
    if _neo4j_driver is not None:
        _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j connection closed")


# PostgreSQL Connection
engine = create_engine(
    resolve_postgres_url(),
    pool_pre_ping=True,
    connect_args=_postgres_connect_args(),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get PostgreSQL database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis Connection
_redis_client: Optional[Redis] = None


def get_redis_client():
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    return _redis_client


def init_db():
    """Initialize database schema via Alembic migrations and load models."""
    # Import models so that all declarative classes are registered in Base.metadata
    import models.repository  # noqa: F401
    import models.service  # noqa: F401
    import models.tech_debt  # noqa: F401

    # Use Alembic migrations as the canonical source of truth.
    from alembic.config import Config
    from alembic import command
    import os

    if settings.skip_alembic_upgrade:
        logger.info("Skipping Alembic upgrade (skip_alembic_upgrade / SKIP_ALEMBIC_UPGRADE is set)")
        return

    alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))

    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database schema migrated to head via Alembic")
    except Exception as e:
        logger.error(f"Failed to migrate database schema: {e}")
        raise
