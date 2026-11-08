"""Migraciones SQL sencillas: ficheros numerados aplicados una sola vez."""

from __future__ import annotations

from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def list_migrations() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


async def applied_versions(conn: asyncpg.Connection) -> set[str]:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    rows = await conn.fetch("SELECT version FROM schema_migrations")
    return {r["version"] for r in rows}


async def migrate(conn: asyncpg.Connection) -> list[str]:
    """Aplica las migraciones pendientes y devuelve sus nombres."""
    done = await applied_versions(conn)
    applied: list[str] = []
    for path in list_migrations():
        version = path.stem
        if version in done:
            continue
        async with conn.transaction():
            await conn.execute(path.read_text(encoding="utf-8"))
            await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", version)
        applied.append(version)
    return applied


async def drop_everything(conn: asyncpg.Connection) -> None:
    """Borra el esquema de Oniel (solo para desarrollo y pruebas)."""
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
