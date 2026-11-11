# Oniel

Web en español para descubrir cómo está conectada la red ferroviaria española. Lo principal es un mapa interactivo en el que se recorre cada línea, con su esquema vertical al lado, y se seleccionan estaciones y tramos; como herramienta secundaria, se simula el cierre hipotético de un tramo en una franja horaria. Está pensada para quien no sabe de ferrocarril y quiere consultar y entender la red de forma clara, intuitiva y atractiva: todo se diseña para esa persona. A quien trabaja en el sector puede serle útil, pero no se diseña nada pensando en él. Hoy carga tres líneas (alta velocidad Madrid – Sevilla, convencional Madrid – Alcázar de San Juan – Córdoba y convencional Manzanares – Ciudad Real, que une las otras dos) con los horarios de Renfe, y está publicada en https://oniel.vercel.app con la API en Render.

Este fichero orienta a una sesión que llega sin contexto. No repite el README ni los documentos de `docs/`: los enlaza.

## Todo en español

Interfaz, documentación, comentarios del código, nombres y mensajes de las pruebas, mensajes de commit y descripciones de PR van en español. Los identificadores del código (`segments`, `stop_mappings`, `fetch_alternatives`) siguen en inglés, como están. Las palabras de la interfaz son las del visitante: «tramo», «estación», «cierre», no jerga; cuando un término técnico es inevitable (PAET, bifurcación), se explica.

## Dónde está cada cosa

- `README.md`: arrancar desde cero, comandos de datos, pruebas y comprobaciones.
- `backend/`: API FastAPI, CLI `oniel-data` (Typer), reglas de simulación en `oniel.sim`, importadores y pruebas pytest. Los módulos se describen en `backend/README.md`.
- `backend/data/raw/`: ficheros originales, con la fecha en el nombre; no se editan. `backend/data/curated/`: una especificación JSON por línea, `sources.json` (el registro de todas las fuentes) e `interrupciones.json` (las interrupciones del servicio, que se revisan a mano como dice `docs/datos.md`).
- `frontend/`: visor React + TypeScript + Vite + MapLibre, con las pruebas Playwright en `frontend/e2e/`. `frontend/public/data/` es la instantánea estática que exporta el importador; el visor arranca siempre con ella.
- [docs/diseno.md](docs/diseno.md): las decisiones de diseño (tokens, tipografía, composición, encuadre, principios).
- [docs/datos.md](docs/datos.md): fuentes y licencias, cómo se verificó cada línea, modelo de datos y el procedimiento «Añadir otra línea».
- [docs/simulacion.md](docs/simulacion.md): método de la simulación, recorrido alternativo, caso comprobado a mano y límites conocidos.
- [docs/despliegue.md](docs/despliegue.md): Vercel (visor), Render (API y PostgreSQL), Logfire y base de datos local.
- [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md): el orden de las tareas pendientes y los principios de arquitectura; el brief de cada tarea está en su incidencia de GitHub (`gh issue view <número>`). Cada sesión nueva coge la siguiente cuyas dependencias estén cerradas.
- `.github/workflows/ci.yml`: lo que comprueba el CI en cada PR y en `main`. `.github/workflows/recordatorio-interrupciones.yml`: abre cada semana una incidencia si toca revisar las interrupciones. `.vscode/`: intérprete `backend/.venv`, Ruff como formateador y pytest desde `backend/`.

## Arrancar y comprobar

Los comandos están en el README y no se repiten aquí: «Arrancar desde cero» (Docker para PostgreSQL, uv y Node 20), «Pruebas» y «Comprobaciones». Antes de abrir una PR tiene que estar todo en verde, que es exactamente lo que ejecuta el CI:

- Backend: `ruff format --check`, `ruff check`, `mypy` (estricto), `pyright` (modo `standard`, el mismo que Pylance), `pytest` con `ONIEL_TEST_DATABASE_URL` apuntando a una base `oniel_test`, y `oniel-data validate`.
- Frontend: `npm run typecheck`, `npm run lint`, `npm run build` y Playwright con `ONIEL_E2E_STATIC=1` (la instantánea estática, sin servidor). Con la API local arrancada, `npx playwright test` sin esa variable prueba también la simulación; hay que pasarlo cuando se toca la simulación o la API.

El editor no debe mostrar avisos que esas órdenes no den: `.vscode/settings.json` fija el intérprete y Ruff, y `backend/pyproject.toml` deja pyright al mismo nivel que Pylance. El frontend no tiene formateador configurado: no se reformatean ficheros enteros.

Para previsualizar el visor desde una sesión, `.claude/launch.json` arranca Vite (`oniel-visor`) con el proxy de la API apuntando al puerto 8010; la API se arranca aparte con `uv run uvicorn oniel.api.main:app --reload --port 8010` desde `backend/`.

## Convenciones

**Tono.** La línea Madrid – Sevilla tuvo dos accidentes graves en 2026: Adamuz (18 de enero) y Urda (28 de octubre). Todo lo que los roce, en la interfaz, en los datos o en la documentación, va en un tono sobrio y neutro: hechos con fecha y fuente, sin adjetivos, sin especular sobre causas ni responsabilidades. Las interrupciones del servicio se describen como lo que son: desde cuándo, según quién y hasta cuándo se prevé.

**Fuentes.** Todo lo que se muestra dice de dónde viene. Cada dato nuevo (una geometría, un horario, un punto kilométrico, el estado de una obra o de un proyecto) entra en `backend/data/curated/sources.json` con id, editor, URL, licencia, fecha de consulta, cobertura y notas, y su fichero crudo va a `backend/data/raw/` con la fecha en el nombre. Sin fuente registrada, el dato no entra. Las licencias se respetan y se citan (`docs/datos.md` y el panel de cobertura del visor).

**Nada personal.** Oniel es una web pública para más gente. No lleva nombres de personas particulares, historias familiares ni opiniones, tampoco en comentarios, datos de prueba o documentación.

**Diseño.** Las decisiones están en `docs/diseno.md` y se siguen: el color solo como señal, una sola familia tipográfica (Archivo), textos cortos y en párrafos, alineación a la izquierda, movimiento solo como respuesta a una acción. Un cambio de diseño es una decisión del usuario, no un efecto secundario de una tarea; si una tarea lo necesita, se propone y, una vez decidido, se anota allí.

**Datos.** Cuando cambian las especificaciones, el GTFS, las fuentes o el exportador, se regenera la instantánea de `frontend/public/data` (`uv run oniel-data import all` la exporta al final; `export snapshot` solo exporta) y se sube en la misma PR, con las tablas de `docs/datos.md` al día. Los recuentos que comprueban las pruebas (viajes por línea, pasos por tramo) se actualizan a la vez y se explican en la PR. Una línea nueva sigue «Añadir otra línea» de `docs/datos.md` paso a paso.

**Pruebas.** Cada regla nueva de simulación o de datos lleva su prueba en `backend/tests/`; cada comportamiento visible nuevo, una prueba Playwright en `frontend/e2e/` que funcione también en modo estático cuando no necesite la API (y `test.skip(estatico, …)` cuando sí la necesite).

**PR pequeñas.** Una tarea por rama y por PR, contra `main`, desde una sesión aislada. La descripción, en español, dice qué cambia, por qué, qué conviene mirar al revisar y qué comprobaciones se han pasado; la PR se abre con las comprobaciones pasadas en local y se espera a que el CI esté en verde. Cuando el CI está en verde y la PR está completa, la misma sesión la fusiona en `main` y actualiza `main` en el checkout local del proyecto (`git pull`), salvo que el usuario haya dicho lo contrario para esa PR. Los mensajes de commit también en español, en una frase que describa el resultado. Al terminar una tarea de `docs/hoja-de-ruta.md`, la misma PR cierra su incidencia, la retira de la lista y lleva lo aprendido a `docs/`. Para que GitHub la cierre al fusionar, la descripción lleva `Closes #N`, tal cual y en inglés: es lo único de la PR que no va en español, porque GitHub no reconoce «Cierra #N».

**Despliegue.** Cada push a `main` despliega las dos mitades: Render la API, y la importación se salta si datos y código no han cambiado; Vercel el visor en https://oniel.vercel.app, salvo que el commit no toque `frontend/`. Cada PR tiene además su vista previa en Vercel, enlazada en la propia PR; conviene abrirla cuando el cambio se ve. Fusionar en `main` es, por tanto, publicar. Fuera de eso no se despliega nada a mano desde una sesión salvo que el usuario lo pida; la CLI de Vercel queda como respaldo (`docs/despliegue.md`).
