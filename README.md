# Oniel

Web en español para entender cómo está conectada la red ferroviaria española. Está pensada para quien no sabe de ferrocarril: un mapa en el que se recorre cada línea, estación a estación, con sus trenes, sus obras y sus cortes, y cada dato con su fuente.

Publicada en **https://oniel.vercel.app**.

Este documento es la puerta de entrada para quien quiera colaborar: qué es cada pieza, cómo arrancarlo en tu equipo y cómo se trabaja aquí.

## Qué hace

- **Mapa de la red, línea a línea.** Cada línea tiene su trazado, su esquema vertical y una ficha por estación y por tramo: kilómetros, vías, velocidad, señalización, ancho.
- **Trenes sobre la vía.** Cuántos trenes pasan al día por cada tramo y de qué operador, y a dónde se llega sin transbordo desde cada estación.
- **Comparar recorridos.** Por dónde se va de una estación a otra y qué diferencia hay entre un camino y otro.
- **Simular un cierre.** Qué trenes se quedan sin paso si se corta un tramo y por dónde podrían desviarse.
- **Lo que está cortado o en obras hoy**, con su fuente y la fecha en que se comprobó, y los proyectos previstos.
- **Glosario** con dibujos, y una página de **cobertura y fuentes** que dice qué hay cargado y de dónde sale.

La red se carga poco a poco. Las líneas cargadas hoy están en la página [Cobertura y fuentes](https://oniel.vercel.app/cobertura) y en [docs/datos.md](docs/datos.md), «Líneas cargadas»; las que vienen, en [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md).

## Cómo está hecho

Oniel tiene dos mitades y un camino de datos que las une:

```
ficheros originales          especificación de cada línea        importador
backend/data/raw/      +     backend/data/curated/*.json    →    oniel-data import all
(trazados de OpenStreetMap,  (nodos, kilómetros, atributos,           │
 horarios GTFS)               fuentes, anotaciones)                   │
                                                          ┌───────────┴───────────┐
                                                          ▼                       ▼
                                                     PostgreSQL           instantánea estática
                                                          │              frontend/public/data/*.json
                                                          ▼                       │
                                                    API (FastAPI)                 │
                                                          └──────────┬────────────┘
                                                                     ▼
                                                        visor (React + MapLibre)
```

- **Backend** (`backend/`, Python 3.13): la API con FastAPI, la orden `oniel-data` que importa y valida los datos, y las reglas de la simulación y de los recorridos. Base de datos PostgreSQL.
- **Visor** (`frontend/`, React + TypeScript + Vite + MapLibre): el mapa y las fichas.
- **La instantánea.** El importador deja en `frontend/public/data/` una copia estática de todo lo que el visor necesita. El visor arranca siempre con ella y pasa a la API cuando responde. Por eso el visor funciona sin backend, y por eso la instantánea se regenera y se sube con cada cambio de datos.

Dos ideas que explican casi todas las decisiones: **todo dato lleva su fuente** (sin fuente registrada, no entra), y **añadir una línea es trabajo de datos**, no de código: el visor dibuja lo que trae la instantánea.

## Empezar

### Solo quiero tocar el visor

No hace falta Docker, ni Python, ni credenciales. Con Node 20 o superior:

```bash
cd frontend && npm install && VITE_DATA_MODE=estatico npm run dev
```

Se abre en http://localhost:5173 con los datos de la instantánea. Todo funciona menos la simulación de cierres, que necesita la API y lo avisa.

### Quiero el proyecto entero

Requisitos: Docker, [uv](https://docs.astral.sh/uv/) y Node 20 o superior. No hace falta ninguna credencial.

1. Levanta PostgreSQL (queda en el puerto 5433, con usuario, contraseña y base `oniel`):

```bash
docker compose up -d
```

2. Instala el backend e importa los datos. `import all` crea las tablas, carga las líneas, las anotaciones y los horarios y exporta la instantánea. Puede tardar unos minutos y es repetible: volver a ejecutarlo deja el mismo estado.

```bash
cd backend && uv sync && uv run oniel-data import all
```

3. Arranca la API, en http://127.0.0.1:8000:

```bash
cd backend && uv run uvicorn oniel.api.main:app --reload
```

4. Arranca el visor, en http://localhost:5173:

```bash
cd frontend && npm install && npm run dev
```

El visor habla con la API a través del proxy de Vite (`/api` → http://127.0.0.1:8000; `ONIEL_API_PROXY` cambia el destino). Si la API no está, se queda en la instantánea.

### Comprobar que todo está bien

```bash
cd backend && uv run oniel-data validate
```

`validate` revisa las líneas, los horarios y las anotaciones sin necesitar base de datos. Si termina sin problemas, los datos están sanos.

## El repositorio por dentro

```
backend/
  src/oniel/        el código: api, cli, network, gtfs, sim, routing, analysis, repo, export…
  data/raw/         ficheros originales, con la fecha en el nombre; no se editan
  data/curated/     una especificación JSON por línea, sources.json (todas las fuentes),
                    anotaciones.json (interrupciones y proyectos) y zonas.json
  tests/            pruebas pytest
frontend/
  src/app/          estado, rutas, capas y atributos
  src/map/          el mapa (MapLibre)
  src/panel/        fichas, lista de líneas, comparador, simulación, glosario
  src/routing/      el cálculo de recorridos, gemelo del que hay en el backend
  public/data/      la instantánea estática que exporta el importador
  e2e/              pruebas Playwright
docs/               diseño, datos, simulación, despliegue, hoja de ruta, capturas
.github/workflows/  CI, refresco semanal de horarios, recordatorio de revisión
```

Los módulos del backend están descritos uno a uno en [backend/README.md](backend/README.md).

Según lo que vayas a hacer, empieza por aquí:

| Quiero… | Lee primero | Toca sobre todo |
|---|---|---|
| Añadir una línea | [docs/datos.md](docs/datos.md), «Añadir otra línea» | `backend/data/curated/`, `backend/data/raw/` |
| Corregir un dato o una fuente | [docs/datos.md](docs/datos.md) | `backend/data/curated/` |
| Registrar un corte, una obra o un proyecto | [docs/datos.md](docs/datos.md), «Interrupciones del servicio» | `backend/data/curated/anotaciones.json` |
| Cambiar algo que se ve | [docs/diseno.md](docs/diseno.md) | `frontend/src/` |
| Tocar la simulación o los recorridos | [docs/simulacion.md](docs/simulacion.md) | `backend/src/oniel/sim`, `routing` y `frontend/src/routing` |
| Tocar el despliegue o la observabilidad | [docs/despliegue.md](docs/despliegue.md) | `render.yaml`, `frontend/vercel.json`, `.github/workflows/` |
| Saber qué hay pendiente | [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md) | — |

## Colaborar

### Cómo entra un cambio

1. **Una incidencia por tarea.** Las tareas están en las [incidencias de GitHub](https://github.com/ebotiab/Oniel/issues), cada una con su porqué, los datos que usa, lo que toca y cuándo se da por hecha. [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md) las ordena.
2. **Una rama y una PR por tarea**, contra `main`. La descripción dice qué cambia, por qué, qué conviene mirar y qué se ha comprobado.
3. **El CI tiene que estar en verde.** `main` está protegida: solo admite cambios por PR y con las comprobaciones `Backend` y `Frontend` pasadas.
4. **Se fusiona con squash, y fusionar publica.** Cada cambio en `main` despliega la API en Render y el visor en Vercel. Cada PR tiene además su vista previa en Vercel.
5. **La PR cierra su incidencia** con `Closes #N` en la descripción, la retira de la hoja de ruta y lleva lo aprendido a `docs/`.

### Convenciones

Están completas en [CLAUDE.md](CLAUDE.md), que es la guía con la que trabajan las sesiones de código y sirve igual a una persona. Lo esencial:

- **Todo en español**: interfaz, documentación, comentarios, nombres de las pruebas, commits y PR. Los identificadores del código siguen en inglés.
- **Se escribe para quien no sabe de ferrocarril.** Lenguaje llano, y los términos técnicos inevitables se explican en el glosario.
- **Sin fuente, el dato no entra.** Cada dato nuevo se registra en `backend/data/curated/sources.json` con editor, URL, licencia y fecha de consulta, y su fichero original va a `backend/data/raw/`. Lo que no se sabe se dice; no se estima.
- **Tono sobrio** en todo lo que roce accidentes o cortes del servicio: hechos con fecha y fuente, sin adjetivos ni causas supuestas.
- **El diseño no cambia de paso.** Las decisiones están en [docs/diseno.md](docs/diseno.md); una nueva se propone antes de implementarla y se anota allí.
- **Cada comportamiento nuevo lleva su prueba**: pytest para reglas y datos, Playwright para lo que se ve.
- **Si cambian los datos, se regenera la instantánea** (`uv run oniel-data import all`) y se sube en la misma PR, con los recuentos de las pruebas al día.

### Antes de abrir la PR

Las comprobaciones rápidas de la mitad que hayas tocado:

```bash
cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pyright
```

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
```

Y las pruebas de lo que hayas tocado (véase «Pruebas»). La batería completa del visor la pasa el CI; no hace falta pasarla en local.

## Pruebas

**Backend.** Un par de minutos:

```bash
cd backend && uv run pytest
```

Las pruebas de integración con PostgreSQL solo corren si existe una base de pruebas y se indica con `ONIEL_TEST_DATABASE_URL`:

```bash
docker exec oniel-postgres createdb -U oniel oniel_test
```

```bash
cd backend && ONIEL_TEST_DATABASE_URL=postgresql://oniel:oniel@localhost:5433/oniel_test uv run pytest
```

**Visor.** Pruebas Playwright, una vez instalado el navegador:

```bash
cd frontend && npx playwright install chromium
```

Mientras trabajas, pasa solo los ficheros de lo que tocas, sobre la instantánea y sin servidor:

```bash
cd frontend && ONIEL_E2E_STATIC=1 npx playwright test e2e/fichas.spec.ts
```

Cosas que conviene saber:

- La batería completa son más de 200 pruebas en dos tamaños de pantalla, escritorio y móvil. La pasa el CI en cada PR, repartida en cuatro trabajos a la vez.
- Cinco ficheros necesitan la API local y el CI no los pasa: `alternativas`, `arranque`, `interrupciones`, `rutas` y `simulacion`. Si tocas la simulación o la API, pásalos a mano con la API arrancada y sin `ONIEL_E2E_STATIC`.
- Playwright arranca Vite por su cuenta en el puerto 5199 (`ONIEL_E2E_PORT` lo cambia) y usa dos procesos en local (`ONIEL_E2E_WORKERS` lo cambia).
- `npm run build` termina comprobando las hojas de estilo compiladas: falla si a alguna le falta una llave. Vercel ejecuta la misma orden, así que una hoja rota no se publica.

## Comandos de datos

Todo pasa por `oniel-data`, desde `backend/`:

```bash
cd backend && uv run oniel-data --help
```

| Comando | Qué hace |
|---|---|
| `import all` | Migra, importa la red, las anotaciones y los horarios, y exporta la instantánea. Con `--if-changed` se salta si datos y código no cambiaron |
| `validate` | Comprueba las líneas, los horarios y las anotaciones sin base de datos (`--spec` para una sola línea) |
| `import network` | Construye cada línea desde el trazado original y su especificación, y la carga |
| `import annotations` | Carga las anotaciones de red (interrupciones y proyectos); la red tiene que estar importada |
| `import gtfs` | Importa cada fichero de horarios declarado en `sources.json`. Repetirlo no duplica nada y un fichero nuevo conserva los anteriores |
| `export snapshot` | Solo exporta la instantánea para el visor |
| `db migrate` / `db reset --yes` | Aplica las migraciones / recrea el esquema (solo en desarrollo) |
| `refresh gtfs` | Descarga los horarios publicados por Renfe y, si han cambiado, guarda el fichero nuevo y lo declara. Lo usa el flujo semanal de GitHub |
| `refresh expiring` | Lista los ficheros de horarios de descarga manual a los que les quedan pocos días de validez |
| `sources` | Lista las fuentes con su licencia y su fecha |
| `obs estado` | Dice qué versión corre en producción, cómo fue su última importación y qué errores hay, según las trazas de Logfire |
| `obs consulta "SQL"` | Consulta de solo lectura sobre esas trazas |
| `logfire-test` | Envía una traza de prueba a Logfire |

Los dos últimos grupos necesitan credenciales de Logfire y solo hacen falta para operar producción ([docs/despliegue.md](docs/despliegue.md)).

## Variables de entorno

Ninguna es obligatoria para desarrollar. Los ejemplos están en `backend/.env.example` y `frontend/.env.example`.

| Variable | Dónde | Para qué |
|---|---|---|
| `ONIEL_DATABASE_URL` o `DATABASE_URL` | backend | La base de datos. Por defecto, la de `docker compose` |
| `ONIEL_TEST_DATABASE_URL` | backend | Activa las pruebas de integración |
| `ONIEL_ENVIRONMENT` | backend | `local` o `production`; etiqueta las trazas |
| `ONIEL_CORS_ORIGINS` | backend | Orígenes que pueden llamar a la API |
| `LOGFIRE_TOKEN` | backend | Envía trazas a Logfire. Sin él no se envía nada y todo funciona igual |
| `ONIEL_API_PROXY` | visor, en desarrollo | A qué API apunta el proxy de Vite |
| `VITE_API_URL` | visor | URL pública de la API. Sin ella, el visor usa la instantánea |
| `VITE_DATA_MODE` | visor | `estatico` fuerza la instantánea aunque haya API |
| `VITE_LOGFIRE_TOKEN` | visor publicado | Envía los errores del navegador a Logfire. En local no hace falta |

## CI y despliegue

- **CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)): en cada PR y en cada cambio de `main` pasa formato, lint, tipos y pruebas del backend con PostgreSQL 17, `oniel-data validate`, y tipos, lint, compilación y Playwright del visor. En una PR mira qué rutas cambian y se salta la mitad a la que el cambio no puede afectar: una de solo documentación no lanza pruebas.
- **Despliegue**: Render sirve la API y PostgreSQL, y reimporta los datos cuando cambian; Vercel sirve el visor. Los dos se actualizan solos al entrar un cambio en `main`. Detalle en [docs/despliegue.md](docs/despliegue.md).
- **Horarios**: un flujo semanal comprueba si Renfe ha publicado horarios nuevos y, si es así, abre una PR con ellos.

## Documentación

- [docs/datos.md](docs/datos.md): fuentes y licencias, líneas cargadas, modelo de datos y cómo añadir una línea.
- [docs/simulacion.md](docs/simulacion.md): cómo se calculan los cierres y los recorridos, con un caso comprobado a mano y sus límites.
- [docs/diseno.md](docs/diseno.md): decisiones de diseño.
- [docs/despliegue.md](docs/despliegue.md): Vercel, Render, Logfire y la base de datos local.
- [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md): tareas pendientes, ordenadas, y principios de arquitectura.
- [CLAUDE.md](CLAUDE.md): convenciones del proyecto.

## Licencias de los datos

- **Horarios**: Renfe Viajeros, CC BY 4.0; Ouigo España, del Punto de Acceso Nacional de Transporte Multimodal (Powered by MITRAMS), con la licencia de datos abiertos del Ministerio de Transportes y Movilidad Sostenible. Iryo no publica sus horarios en un formato abierto y sus trenes no están.
- **Trazado**: colaboradores de OpenStreetMap, ODbL.
- **Verificación**: Adif.
- **Mapa base**: OpenFreeMap / OpenMapTiles / OpenStreetMap.

El detalle de cada fuente, con su URL y su fecha de consulta, está en [docs/datos.md](docs/datos.md) y en la página [Cobertura y fuentes](https://oniel.vercel.app/cobertura).
