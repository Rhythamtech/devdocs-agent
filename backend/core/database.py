"""PostgreSQL connection pool and application schema.

Agno stores its sessions in the ``ai`` schema using its own SQLAlchemy
engine.  The rest of the API (users and future auth/audit tables) uses this
async psycopg pool so FastAPI request handlers never block the event loop.
"""

from typing import Any, Optional, Sequence

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from core.config import settings

# Keep these in sync with the Agno PostgresDb configuration in agent.py.
AGNO_DB_SCHEMA = "ai"
AGNO_SESSIONS_TABLE = "agno_sessions"

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        hash_password TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        revoked_at TIMESTAMPTZ
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
        prompt_length INTEGER,
        model TEXT,
        latency_ms INTEGER,
        status TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    f"CREATE SCHEMA IF NOT EXISTS {AGNO_DB_SCHEMA}",
    """
    CREATE TABLE IF NOT EXISTS voice_transcripts (
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (user_id, session_id, message_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_voice_transcripts_user_session ON voice_transcripts (user_id, session_id, created_at)",
    f"""
    CREATE TABLE IF NOT EXISTS {AGNO_DB_SCHEMA}.{AGNO_SESSIONS_TABLE} (
        session_id VARCHAR PRIMARY KEY,
        session_type VARCHAR NOT NULL,
        agent_id VARCHAR,
        team_id VARCHAR,
        workflow_id VARCHAR,
        user_id VARCHAR,
        session_data JSONB,
        agent_data JSONB,
        team_data JSONB,
        workflow_data JSONB,
        metadata JSONB,
        runs JSONB,
        summary JSONB,
        created_at BIGINT NOT NULL,
        updated_at BIGINT
    )
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_{AGNO_SESSIONS_TABLE}_session_type
        ON {AGNO_DB_SCHEMA}.{AGNO_SESSIONS_TABLE} (session_type)
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_{AGNO_SESSIONS_TABLE}_created_at
        ON {AGNO_DB_SCHEMA}.{AGNO_SESSIONS_TABLE} (created_at)
    """,
)


class Database:
    """Small async wrapper around a psycopg connection pool."""

    def __init__(self, url: str) -> None:
        self._pool = AsyncConnectionPool(
            conninfo=url,
            min_size=1,
            max_size=10,
            open=False,
            # Validate pooled connections before handing them out so a
            # Postgres restart doesn't surface as a 500 on the next request.
            check=AsyncConnectionPool.check_connection,
            # Every application query is an independent unit of work.  Agno
            # manages its own transactions through SQLAlchemy.
            kwargs={"row_factory": dict_row, "autocommit": True},
        )

    async def connect(self) -> None:
        try:
            await self._pool.open(wait=True, timeout=settings.POSTGRES_CONNECT_TIMEOUT)
            async with self._pool.connection() as conn:
                for statement in SCHEMA_STATEMENTS:
                    await conn.execute(statement)
        except Exception:
            await self._pool.close()
            raise

    async def close(self) -> None:
        await self._pool.close()

    async def fetchrow(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> Optional[dict[str, Any]]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()

    async def fetch(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> list[dict[str, Any]]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()

    async def execute(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> int:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.rowcount
