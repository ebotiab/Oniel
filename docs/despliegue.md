# Despliegue de Oniel

## Visor en Vercel

Proyecto `oniel` en la cuenta personal de Vercel, directorio raíz `frontend/` (hay un `frontend/vercel.json` con el framework y la carpeta de salida).

```bash
cd frontend && vercel login
```

```bash
cd frontend && vercel link --project oniel --yes && vercel deploy
```

La primera vez, `vercel link` ofrece crear el proyecto. Variables de entorno del proyecto:

- `VITE_API_URL`: URL pública de la API en Render (por ejemplo `https://oniel-api.onrender.com`). Sin ella, el visor sirve la instantánea estática de `frontend/public/data` y la simulación avisa de que necesita el servidor.

Conviene regenerar la instantánea (`uv run oniel-data export snapshot`) antes de cada despliegue para que la vista estática esté al día.

## API, PostgreSQL e importador en Render

`render.yaml` describe un Blueprint con:

- `oniel-postgres`: PostgreSQL 17 (plan free).
- `oniel-api`: servicio web Docker (`backend/Dockerfile`), `healthCheckPath: /healthz`, con `DATABASE_URL` enlazada a la base.
- `oniel-importer`: cron job con la misma imagen que ejecuta `oniel-data import all` (los lunes a las 5:00 UTC; también se lanza a mano desde el panel).

Pasos: Dashboard → Blueprints → New Blueprint Instance → repositorio `ebotiab/Oniel`. Render pide el valor de `LOGFIRE_TOKEN` (marcado `sync: false`). Tras el primer despliegue, ejecutar el job `oniel-importer` una vez (o `oniel-data import all` en la shell del servicio) para cargar los datos.

`ONIEL_CORS_ORIGINS` debe incluir el dominio del visor (`["https://oniel.vercel.app"]` por defecto); los dominios de vista previa `*.vercel.app` se aceptan por expresión regular.

## Logfire

Proyecto `oniel` en la organización personal `ebotiab` (región US): https://logfire-us.pydantic.dev/ebotiab/oniel

- Servicios: `oniel-api` (FastAPI + asyncpg) y `oniel-data` (importador y CLI).
- En local, el SDK lee `backend/.logfire/logfire_credentials.json` (no se versiona). Sin ese fichero ni `LOGFIRE_TOKEN` no se envía nada.
- En Render, definir `LOGFIRE_TOKEN` con un token de escritura del proyecto (Logfire → proyecto `oniel` → Settings → Write tokens).
- Comprobación: `uv run oniel-data logfire-test` envía una traza; las trazas de la API aparecen al usar cualquier endpoint.

## Base de datos local

`docker-compose.yml` levanta PostgreSQL 17 en el puerto 5433 con usuario, contraseña y base `oniel`. El esquema se crea con `oniel-data db migrate`; las migraciones viven en `backend/src/oniel/db/migrations/`.
