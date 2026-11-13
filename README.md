# Oniel

Web en español para descubrir cómo está conectada la red ferroviaria española. Se abre con un mapa interactivo en el que se recorre la línea, se seleccionan estaciones y tramos y, como herramienta secundaria, se simula un cierre hipotético de un tramo en una franja horaria.

Esta versión cubre once líneas: la **línea de alta velocidad Madrid–Sevilla** (Adif, línea 010), incluidos los entornos de Urda y Adamuz; la **línea convencional Madrid–Aranjuez–Alcázar de San Juan–Manzanares–Despeñaperros–Linares-Baeza–Córdoba** (la antigua línea de Andalucía, tramos de las líneas 300 y 400 de Adif), y la **línea convencional Manzanares–Ciudad Real** (Adif, línea 522, de vía única), que une las otras dos; el **ramal convencional Espelúy–Jaén** (Adif, línea 402, de vía única), que sale de la segunda; la **línea convencional Linares-Baeza–Moreda–Granada** (Adif, líneas 410 y 416, de vía única y sin electrificar), el camino convencional a Granada; la **línea convencional Alcázar de San Juan–Albacete** (el trecho central de la línea 300 de Adif, de vía doble), la rama de Levante; la **línea de alta velocidad Córdoba–Málaga** (Adif, línea 030), hasta Málaga-María Zambrano; la **línea de alta velocidad Antequera–Granada** (Adif, línea 036), el camino por el que hoy van los trenes a Granada; la **línea de alta velocidad Madrid–Zaragoza–Barcelona** (Adif, línea 050); la **línea de alta velocidad Madrid–Cuenca–Valencia** (Adif, línea 040), desde la bifurcación de Torrejón de Velasco, y la **línea convencional Valencia–Castellón–Camp de Tarragona** (Adif, líneas 600 y 640), el Corredor Mediterráneo entre las dos anteriores, con los servicios de Renfe que las recorren y los de Ouigo en la alta velocidad a Sevilla, a Málaga, a Barcelona y a Valencia (Iryo no publica sus horarios en un formato abierto y sus trenes no están). Comparten nodos (Madrid-Puerta de Atocha, Córdoba, Manzanares, Ciudad Real, Espelúy, Linares-Baeza, Alcázar de San Juan, la bifurcación de Málaga, Antequera-Santa Ana, Granada, la bifurcación de Torrejón de Velasco, València-Joaquín Sorolla y Camp de Tarragona), así que la simulación de un cierre señala los recorridos alternativos cuando existen, por una línea o por varias encadenadas. Los horarios son los planificados; las interrupciones vigentes del servicio (obras, cortes tras un accidente) se registran a mano en `backend/data/curated/anotaciones.json`, con su fuente y la fecha de comprobación, y el visor las marca en rojo.

- Diseño: [docs/diseno.md](docs/diseno.md)
- Datos y procedencia: [docs/datos.md](docs/datos.md)
- Método de simulación y caso comprobado a mano: [docs/simulacion.md](docs/simulacion.md)
- Despliegue (Vercel, Render, Logfire): [docs/despliegue.md](docs/despliegue.md)
- Tareas pendientes, ordenadas: [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md)
- Guía para las sesiones de código (qué es Oniel, dónde está cada cosa, convenciones): [CLAUDE.md](CLAUDE.md)

## Estructura

```
backend/   API FastAPI, CLI de datos (Typer), reglas de simulación, pruebas pytest
  data/    raw/ (ficheros originales), curated/ (especificación de cada línea, fuentes y anotaciones de red)
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

`import all` migra la base de datos, importa la red de las líneas cargadas, las anotaciones de red (hoy, las interrupciones del servicio) y los horarios y exporta la instantánea estática a `frontend/public/data`. Es repetible: volver a ejecutarlo deja el mismo estado.

Opcional, para los agentes de código: `uvx library-skills --claude` en la raíz enlaza en `.claude/skills` y `.agents/skills` las skills que traen FastAPI y Typer (apuntan a `backend/.venv`, por eso no están en git).

```bash
cd backend && uv run uvicorn oniel.api.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

El visor queda en http://localhost:5173 y habla con la API a través del proxy de Vite (`/api` → http://127.0.0.1:8000; cambia el destino con `ONIEL_API_PROXY`). El visor arranca siempre con la instantánea estática de `frontend/public/data` y pasa a la API en cuanto responde; sin API, se queda en la instantánea y la simulación avisa de que necesita el servidor.

## Comandos de datos

```bash
cd backend && uv run oniel-data --help
```

| Comando | Qué hace |
|---|---|
| `db migrate` / `db reset --yes` | Aplica migraciones / recrea el esquema (solo desarrollo) |
| `import network` | Construye cada línea desde la geometría cruda y la especificación curada y la carga (`--spec` repetible; sin él, todas) |
| `import annotations` | Carga las anotaciones de red (hoy, las interrupciones del servicio) de `curated/anotaciones.json`; la red tiene que estar importada |
| `import gtfs` | Importa cada fichero de horarios declarado en `sources.json` (o el de `--feed`) como un conjunto de datos: los servicios que recorren las líneas cargadas y su paso por cada tramo. Repetirlo no duplica nada y un fichero nuevo conserva los anteriores |
| `import all` | Todo lo anterior más la exportación estática; con `--if-changed` se salta si datos y código no cambiaron desde la última |
| `validate` | Comprueba la red, la resolución de cada fichero de horarios declarado y las anotaciones de red sin base de datos (`--spec` repetible; sin él, todas) |
| `export snapshot` | Exporta JSON estático para el visor |
| `refresh gtfs` | Descarga el GTFS publicado por Renfe y, si cambian los trenes de las líneas cargadas en las próximas cuatro semanas o el fichero cargado tiene 28 días o más, guarda el nuevo y lo declara en `sources.json`; después tocan `validate` e `import all`. Lo usa el flujo semanal `.github/workflows/gtfs.yml` (`docs/datos.md`, «Refresco de los horarios») |
| `refresh expiring` | Lista los ficheros de horarios de descarga manual a los que les quedan pocos días de validez |
| `sources` | Lista las fuentes con licencia y fecha |
| `logfire-test` | Envía una traza de prueba a Logfire |
| `obs estado` | Dice qué commit corre en producción, la última importación y los errores, según las trazas de Logfire (`docs/despliegue.md`) |
| `obs consulta "SQL"` | Ejecuta una consulta de solo lectura sobre las trazas |

## Pruebas

```bash
cd backend && uv run pytest
```

Las pruebas de integración con PostgreSQL se activan con `ONIEL_TEST_DATABASE_URL` (por ejemplo `postgresql://oniel:oniel@localhost:5433/oniel_test`, tras `docker exec oniel-postgres createdb -U oniel oniel_test`).

```bash
cd frontend && npm run typecheck && npx playwright install chromium && npx playwright test
```

Playwright arranca Vite por su cuenta y espera la API en `ONIEL_API_PROXY` (por defecto http://127.0.0.1:8000). Con `ONIEL_E2E_STATIC=1` prueba la instantánea estática sin servidor (sin simulación). Si otra sesión ocupa el puerto 5199, `ONIEL_E2E_PORT` lo cambia. En local usa dos procesos, para que varias sesiones a la vez no saturen el equipo; `ONIEL_E2E_WORKERS=4` lo sube cuando se prueba a solas.

La batería completa son más de 200 pruebas en dos tamaños de pantalla. Mientras se trabaja basta con los ficheros de lo que se toca, sobre la instantánea:

```bash
cd frontend && ONIEL_E2E_STATIC=1 npx playwright test e2e/fichas.spec.ts
```

La batería entera sobre la instantánea la pasa el CI en cada pull request. Las pruebas que necesitan la API local (sin `ONIEL_E2E_STATIC`) no las pasa el CI: cuando se toca la simulación o la API hay que pasar a mano sus ficheros (`alternativas`, `arranque`, `interrupciones`, `rutas` y `simulacion`).

## Comprobaciones

```bash
cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pyright
```

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

Ruff formatea y ordena importaciones; mypy (estricto) y pyright (modo `standard`, el mismo que Pylance) tipan el backend; `tsc` y oxlint cubren el visor, incluidas las pruebas Playwright. `npm run build` compila el visor y termina con `frontend/scripts/comprobar-css.mjs`, que falla si a una hoja de estilos le falta una llave o si las reglas de base (`:root`, `body`) no quedan en el primer nivel de la hoja compilada: las pruebas Playwright corren contra el servidor de desarrollo y no ven un fallo que solo aparece al compilar. Vercel ejecuta la misma orden, así que una hoja rota no se publica. El directorio `.vscode/` fija el intérprete de `backend/.venv` y Ruff como formateador, de modo que el editor no muestre avisos que estas órdenes no muestren.

El CI de GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) ejecuta estas mismas órdenes y las pruebas en cada pull request y en cada push a `main`: el backend con PostgreSQL 17 (incluidas las pruebas de integración y `oniel-data validate`) y el visor con Node 20 y Playwright sobre la instantánea estática.

Para que tarde poco, la batería de Playwright va repartida en cuatro fragmentos que corren a la vez (`--shard`), y las trazas de las pruebas que fallen se guardan por fragmento. En una pull request, el CI mira además qué rutas cambian y salta la mitad a la que el cambio no puede afectar ([.github/scripts/que-cambia.sh](.github/scripts/que-cambia.sh)): una de solo documentación no lanza pruebas. `main` exige las comprobaciones `Backend` y `Frontend`, que son dos trabajos finales que resumen a los demás y quedan en verde también cuando su mitad se salta. En un push a `main` corre siempre todo.

## Variables de entorno

Backend (`backend/.env.example`): `DATABASE_URL` u `ONIEL_DATABASE_URL`, `ONIEL_ENVIRONMENT`, `ONIEL_CORS_ORIGINS`, `LOGFIRE_TOKEN`. Sin `LOGFIRE_TOKEN` (ni `backend/.logfire/`) no se envía telemetría y todo funciona igual.

Frontend (`frontend/.env.example`): `VITE_API_URL` (URL pública de la API) y `VITE_DATA_MODE=estatico` para forzar la instantánea. `VITE_LOGFIRE_TOKEN` solo lo usa el visor publicado en producción, para enviar sus errores a Logfire (`docs/despliegue.md`, «Errores del visor»); en local no hace falta.

## Licencias de los datos

Horarios: Renfe Viajeros, CC BY 4.0; Ouigo España, del Punto de Acceso Nacional de Transporte Multimodal (Powered by MITRAMS), con la licencia de datos abiertos del Ministerio de Transportes y Movilidad Sostenible. Trazado: colaboradores de OpenStreetMap, ODbL. Verificación: Adif. Mapa base: OpenFreeMap / OpenMapTiles / OpenStreetMap. Detalle en [docs/datos.md](docs/datos.md).
