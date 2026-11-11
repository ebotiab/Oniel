# Oniel · backend

API FastAPI, CLI de datos (`oniel-data`, Typer) y reglas de simulación. Las instrucciones completas están en el [README raíz](../README.md).

```bash
uv sync
uv run oniel-data import all
uv run uvicorn oniel.api.main:app --reload
uv run pytest
```

Módulos: `oniel.api` (rutas), `oniel.cli` (importación y validación), `oniel.network` (construcción de la línea e interrupciones del servicio), `oniel.gtfs` (lectura e importación de horarios, un conjunto de datos por fichero), `oniel.sim` (reglas puras de paso y cierre), `oniel.repo` (consultas asyncpg), `oniel.export` (instantánea estática), `oniel.observability` (Logfire).
