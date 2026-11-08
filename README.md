# Oniel

Web en español para descubrir cómo está conectada la red ferroviaria española. Se abre con un mapa interactivo en el que se recorre la línea, se seleccionan estaciones y tramos y, como herramienta secundaria, se simula un cierre hipotético de un tramo en una franja horaria.

Esta primera versión cubre la **línea de alta velocidad Madrid–Sevilla** (Adif, línea 010), incluidos los entornos de Urda y Adamuz, con los servicios de Renfe que la recorren.

- Diseño: [docs/diseno.md](docs/diseno.md)
- Datos y procedencia: [docs/datos.md](docs/datos.md)
- Método de simulación y caso comprobado a mano: [docs/simulacion.md](docs/simulacion.md)
- Despliegue (Vercel, Render, Logfire): [docs/despliegue.md](docs/despliegue.md)

## Estructura

```
backend/   API FastAPI, CLI de datos (Typer), reglas de simulación, pruebas pytest
  data/    raw/ (ficheros originales), curated/ (especificación de la línea y fuentes)
frontend/  Visor React + TypeScript + Vite + MapLibre, pruebas Playwright
docs/      Diseño, datos, simulación, despliegue, capturas
render.yaml, docker-compose.yml, backend/Dockerfile
```

## Arrancar desde cero

Requisitos: Docker, [uv](https://docs.astral.sh/uv/) y Node 20 o superior. No hace falta ninguna credencial.

```bash
docker compose up -d
```

```bash
cd backend && uv sync && uv run oniel-data import all
```

`import all` migra la base de datos, importa la red y los horarios y exporta la instantánea estática a `frontend/public/data`. Es repetible: volver a ejecutarlo deja el mismo estado.

```bash
cd backend && uv run fastapi dev
```

```bash
cd frontend && npm install && npm run dev
```

El visor queda en http://localhost:5173 y habla con la API a través del proxy de Vite (`/api` → http://127.0.0.1:8000; cambia el destino con `ONIEL_API_PROXY`). Sin API, el visor muestra la instantánea estática y la simulación avisa de que necesita el servidor.

## Comandos de datos

```bash
cd backend && uv run oniel-data --help
```

| Comando | Qué hace |
|---|---|
| `db migrate` / `db reset --yes` | Aplica migraciones / recrea el esquema (solo desarrollo) |
| `import network` | Construye la línea desde la geometría cruda y la especificación curada y la carga |
| `import gtfs` | Importa los servicios del GTFS que recorren la línea y precalcula su paso por cada tramo |
| `import all` | Todo lo anterior más la exportación estática |
| `validate` | Comprueba la red y la resolución de horarios sin base de datos |
| `export snapshot` | Exporta JSON estático para el visor |
| `sources` | Lista las fuentes con licencia y fecha |
| `logfire-test` | Envía una traza de prueba a Logfire |

## Pruebas

```bash
cd backend && uv run pytest
```

Las pruebas de integración con PostgreSQL se activan con `ONIEL_TEST_DATABASE_URL` (por ejemplo `postgresql://oniel:oniel@localhost:5433/oniel_test`, tras `docker exec oniel-postgres createdb -U oniel oniel_test`).

```bash
cd frontend && npm run typecheck && npx playwright install chromium && npx playwright test
```

Playwright arranca Vite por su cuenta y espera la API en `ONIEL_API_PROXY` (por defecto http://127.0.0.1:8000). Con `ONIEL_E2E_STATIC=1` prueba la instantánea estática sin servidor (sin simulación).

## Comprobaciones

```bash
cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pyright
```

```bash
cd frontend && npm run typecheck && npm run lint
```

Ruff formatea y ordena importaciones; mypy (estricto) y pyright (modo `standard`, el mismo que Pylance) tipan el backend; `tsc` y oxlint cubren el visor, incluidas las pruebas Playwright. El directorio `.vscode/` fija el intérprete de `backend/.venv` y Ruff como formateador, de modo que el editor no muestre avisos que estas órdenes no muestren.

## Variables de entorno

Backend (`backend/.env.example`): `DATABASE_URL` u `ONIEL_DATABASE_URL`, `ONIEL_ENVIRONMENT`, `ONIEL_CORS_ORIGINS`, `LOGFIRE_TOKEN`. Sin `LOGFIRE_TOKEN` (ni `backend/.logfire/`) no se envía telemetría y todo funciona igual.

Frontend (`frontend/.env.example`): `VITE_API_URL` (URL pública de la API) y `VITE_DATA_MODE=estatico` para forzar la instantánea.

## Licencias de los datos

Horarios: Renfe Viajeros, CC BY 4.0. Trazado: colaboradores de OpenStreetMap, ODbL. Verificación: Adif. Mapa base: OpenFreeMap / OpenMapTiles / OpenStreetMap. Detalle en [docs/datos.md](docs/datos.md).
