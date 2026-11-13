# Oniel · backend

API FastAPI, CLI de datos (`oniel-data`, Typer) y reglas de simulación. Las instrucciones completas están en el [README raíz](../README.md).

```bash
uv sync
uv run oniel-data import all
uv run uvicorn oniel.api.main:app --reload
uv run pytest
```

Módulos: `oniel.api` (rutas), `oniel.analysis` (trenes por tramo y si la red cargada les ofrece otro camino), `oniel.cli` (importación y validación), `oniel.network` (construcción de la línea, reparto de los atributos de tramo declarados por secciones y anotaciones de red, con las interrupciones del servicio como primer tipo), `oniel.gtfs` (lectura, un tren por número y día, importación y refresco de horarios, un conjunto de datos por fichero), `oniel.sim` (reglas puras de paso y cierre), `oniel.routing` (grafo de todas las líneas, escenarios y recorridos entre dos nodos), `oniel.repo` (consultas asyncpg), `oniel.export` (instantánea estática: un índice ligero de la red y un fichero por línea), `oniel.observability` (Logfire: las trazas llevan el commit desplegado, y aquí se decide qué no se envía), `oniel.obs` (estado de producción leído de esas trazas, `oniel-data obs`).
