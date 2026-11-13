"""Configuración leída del entorno. Todo funciona en local sin credenciales."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ONIEL_", env_file=".env", extra="ignore")

    # Render inyecta DATABASE_URL; en local usamos el contenedor de docker-compose.
    database_url: str = Field(
        default="postgresql://oniel:oniel@localhost:5433/oniel",
        validation_alias=AliasChoices("ONIEL_DATABASE_URL", "DATABASE_URL"),
    )
    environment: str = Field(
        default="local", validation_alias=AliasChoices("ONIEL_ENVIRONMENT", "LOGFIRE_ENVIRONMENT")
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    data_dir: Path = BACKEND_DIR / "data"
    default_line_id: str = "lav-madrid-sevilla"
    #: Líneas cargadas por `import all`, en orden: la primera define los nodos compartidos.
    line_ids: list[str] = [
        "lav-madrid-sevilla",
        "convencional-madrid-alcazar-cordoba",
        "manzanares-ciudad-real",
        "espeluy-jaen",
        "linares-baeza-moreda-granada",
        "alcazar-albacete",
        "lav-cordoba-malaga",
        "lav-antequera-granada",
        "lav-madrid-barcelona",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
