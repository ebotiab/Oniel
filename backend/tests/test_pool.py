"""La cadena de conexión que llega del entorno, tal como la entiende asyncpg."""

from __future__ import annotations

from oniel.db.pool import normalize_dsn


def test_una_cadena_sin_parametros_no_cambia() -> None:
    dsn = "postgresql://oniel:oniel@localhost:5433/oniel"
    assert normalize_dsn(dsn) == dsn


def test_los_parametros_que_asyncpg_entiende_se_conservan() -> None:
    dsn = "postgresql://usuario:clave@servidor.example/oniel?sslmode=require"
    assert normalize_dsn(dsn) == dsn


def test_channel_binding_se_quita_y_lo_demas_queda() -> None:
    dsn = (
        "postgresql://usuario:clave@servidor.example/oniel?sslmode=require&channel_binding=require"
    )
    assert normalize_dsn(dsn) == "postgresql://usuario:clave@servidor.example/oniel?sslmode=require"


def test_una_cadena_con_solo_channel_binding_queda_sin_parametros() -> None:
    dsn = "postgresql://usuario:clave@servidor.example/oniel?channel_binding=require"
    assert normalize_dsn(dsn) == "postgresql://usuario:clave@servidor.example/oniel"
