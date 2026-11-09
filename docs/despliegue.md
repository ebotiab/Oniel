# Despliegue de Oniel

## Visor en Vercel

Proyecto `oniel` en la cuenta personal de Vercel, directorio raíz `frontend/` (hay un `frontend/vercel.json` con el framework y la carpeta de salida).

```bash
cd frontend && vercel login
```

```bash
cd frontend && vercel link --project oniel --yes && vercel deploy
```

Para publicar en producción (https://oniel.vercel.app):

```bash
cd frontend && env -u HTTPS_PROXY -u HTTP_PROXY vercel --prod
```

Estado (9 de noviembre de 2026): el proyecto `oniel` existe en el ámbito personal `enrique-botia-barbera-s-projects`. La producción https://oniel.vercel.app sirve el commit `e4eb6e0` de `main` (pestañas de línea, esquema filtrado por línea y rótulos sin solapar), publicado el 9 de noviembre de 2026 con `vercel --prod` desde `frontend/` (despliegue `dpl_FMqoPxba1xw5RHsEQSYTCYZXZBAU`). Vercel no está conectado a git: cada publicación es manual con la CLI, así que tras fusionar cambios del visor en `main` hay que repetir el despliegue. El enlace local está en `frontend/.vercel/` (ignorado por git; en un worktree nuevo basta con copiar su `project.json`). Nota: la CLI falla con `fetch failed` si las variables `HTTPS_PROXY`/`HTTP_PROXY` apuntan a un proxy local; ejecutarla sin ellas (`env -u HTTPS_PROXY -u HTTP_PROXY vercel …`).

Variables de entorno del proyecto:

- `VITE_API_URL`: URL pública de la API en Render. Está fijada a `https://oniel-api-5e63.onrender.com` en los entornos Production y Preview de Vercel (8 de noviembre de 2026). Sin ella, el visor sirve la instantánea estática de `frontend/public/data` y la simulación avisa de que necesita el servidor. Si la API no responde (por ejemplo mientras Render la despierta), el visor cae por sí solo a la instantánea.

Conviene regenerar la instantánea (`uv run oniel-data export snapshot`) antes de cada despliegue para que la vista estática esté al día.

## API y PostgreSQL en Render

`render.yaml` es un Blueprint de Render con:

- `oniel-postgres`: PostgreSQL 17, plan free, región Frankfurt.
- `oniel-api`: servicio web Docker (`backend/Dockerfile`, `rootDir: backend`), plan free, `healthCheckPath: /healthz`, `DATABASE_URL` enlazada a la base y `LOGFIRE_TOKEN` marcado `sync: false` (se aporta al aprobar el primer sync).
- `oniel-importer` (cron job, comentado): Render no ofrece cron jobs gratuitos y pide un método de pago en el workspace para crearlos. Para activarlo, añade un método de pago, descomenta el bloque y haz push.

Estado (8 de noviembre de 2026): Blueprint `oniel` (`exs-dbo9l3gu01pc73ekfu2g`) en el workspace "My Workspace" de la cuenta personal, creado desde el conector MCP de Render con `existingResources: create_new`, por lo que Render añadió el sufijo `-5e63` a los recursos: base `oniel-postgres-5e63` y API `oniel-api-5e63`, publicada en https://oniel-api-5e63.onrender.com. Con `autoSync` activo, cada push a `main` vuelve a desplegar la API y aplica los cambios del Blueprint.

Límites del plan gratuito, que conviene conocer:

- La API se suspende tras 15 minutos sin tráfico y la primera petición después tarda alrededor de un minuto. El visor lo tolera: mientras tanto sirve la instantánea estática y la simulación avisa.
- La base gratuita caduca a los 30 días de su creación (el 8 de diciembre de 2026). Todos los datos se regeneran con el importador a partir de los archivos del repositorio, así que no se pierde nada irrecuperable. Para una base persistente, cambia `plan: free` por `basic-256mb` en `render.yaml` (requiere método de pago) y haz push.

### Cargar o refrescar los datos

Sin cron job, la API carga los datos ella misma: con `ONIEL_IMPORT_ON_START=1` (fijado en `render.yaml`), `backend/docker-entrypoint.sh` ejecuta `oniel-data import all` antes de arrancar el servidor. Tarda unos 5 segundos y es idempotente, así que cada despliegue y cada arranque tras una suspensión dejan la base alineada con los archivos del repositorio. Si más adelante se activa el cron job, basta con quitar esa variable.

También puede lanzarse desde cualquier máquina con `uv` y acceso a la base. La URL externa (External Database URL) está en el panel de la base en Render; no la guardes en el repositorio.

```bash
cd backend && ONIEL_DATABASE_URL='<External Database URL>' uv run oniel-data import all
```

La importación es repetible: crea el esquema si falta, sustituye los servicios de la fuente dentro de una transacción y registra la ejecución en `import_runs`. También regenera la instantánea estática de `frontend/public/data`, que conviene subir junto con los cambios.

`ONIEL_CORS_ORIGINS` debe incluir el dominio del visor (`["https://oniel.vercel.app"]` por defecto); los dominios de vista previa `*.vercel.app` se aceptan por expresión regular.

## Logfire

Proyecto `oniel` en la organización personal `ebotiab` (región US): https://logfire-us.pydantic.dev/ebotiab/oniel

- Servicios: `oniel-api` (FastAPI + asyncpg) y `oniel-data` (importador y CLI).
- En local, el SDK lee `backend/.logfire/logfire_credentials.json` (no se versiona). Sin ese fichero ni `LOGFIRE_TOKEN` no se envía nada.
- En Render, definir `LOGFIRE_TOKEN` con un token de escritura del proyecto (Logfire → proyecto `oniel` → Settings → Write tokens).
- Comprobación: `uv run oniel-data logfire-test` envía una traza; las trazas de la API aparecen al usar cualquier endpoint.

## Base de datos local

`docker-compose.yml` levanta PostgreSQL 17 en el puerto 5433 con usuario, contraseña y base `oniel`. El esquema se crea con `oniel-data db migrate`; las migraciones viven en `backend/src/oniel/db/migrations/`.
