# Despliegue de Oniel

## Visor en Vercel

Proyecto `oniel` en la cuenta personal de Vercel (ámbito `enrique-botia-barbera-s-projects`), conectado desde el 11 de noviembre de 2026 al repositorio `ebotiab/Oniel`, con directorio raíz `frontend` y rama de producción `main`. Lo demás está en `frontend/vercel.json`: el framework (Vite), la orden de compilación, la carpeta de salida, las cabeceras de caché y cuándo se salta una compilación. La orden de compilación (`npm run build`) termina comprobando las hojas de estilo compiladas (`frontend/scripts/comprobar-css.mjs`): si a una le falta una llave o las reglas de base quedan anidadas, la compilación falla y ese despliegue no se publica. Se añadió el 12 de noviembre de 2026, después de que una llave sin cerrar dejara producción sin estilos entre las PR 75 y 82.

### Despliegue automático

Una fusión en `main` compila el visor y lo publica en https://oniel.vercel.app, sin pasos manuales. Render despliega la API con ese mismo push, así que las dos mitades salen del mismo commit. La instantánea que se publica es la de `frontend/public/data` en `main`: cuando cambian los datos se regenera (`uv run oniel-data export snapshot`) y se sube en la misma PR.

Cada rama que se sube tiene además su vista previa, con una dirección propia. En la PR aparece la comprobación «Vercel», cuyo enlace «Details» lleva a la vista previa. Vercel no comenta en las PR ni en los commits: está desactivado en el proyecto (Settings → Git → «Pull Request Comments» y «Commit Comments»), porque cada comentario suponía un correo de GitHub al autor. La opción `github.silent` de `vercel.json` no lo evita. Las vistas previas usan la misma API que producción (`VITE_API_URL` en el entorno Preview) y el backend acepta su origen. Están protegidas por Vercel Authentication: solo se abren con la sesión iniciada en la cuenta de Vercel del proyecto. La dirección de producción es pública. Una PR que llega desde un fork no se despliega hasta que se autoriza en Vercel.

Vercel se salta la compilación cuando nada ha cambiado dentro de `frontend/` desde el último despliegue correcto de esa rama (`ignoreCommand` en `frontend/vercel.json`). Una fusión que solo toca el backend o la documentación deja producción como estaba. En una PR, el primer push de la rama siempre compila, de modo que toda PR tiene vista previa, y los siguientes solo si tocan `frontend/`. Cuando se salta, la comprobación «Vercel» queda en verde con el texto «Canceled by Ignored Build Step» y el comentario conserva el enlace a la última vista previa compilada. Si la comparación no puede hacerse, se compila.

Para saber qué commit sirve producción: `vercel inspect oniel.vercel.app`, o la comprobación «Vercel» del commit en `main`, que enlaza a su despliegue.

### La CLI como respaldo

Sirve si la integración con GitHub falla o si hay que volver a publicar sin un commit nuevo. Como el directorio raíz está fijado en el proyecto, la CLI se ejecuta desde la raíz del repositorio, no desde `frontend/`.

```bash
vercel login
```

```bash
vercel link --project oniel --yes
```

```bash
env -u HTTPS_PROXY -u HTTP_PROXY vercel --prod
```

Al enlazar, la CLI deja `.vercel/` y un `.env.local` con un token temporal; git ignora los dos. La CLI falla con `fetch failed` si las variables `HTTPS_PROXY`/`HTTP_PROXY` apuntan a un proxy local, y por eso se ejecuta sin ellas. Sin terminal interactiva hace falta `--yes` y la CLI responde en JSON.

### Variables de entorno

- `VITE_API_URL`: URL pública de la API en Render. Está fijada a `https://oniel-api-5e63.onrender.com` en los entornos Production y Preview de Vercel (8 de noviembre de 2026). Sin ella, el visor sirve la instantánea estática de `frontend/public/data` y la simulación avisa de que necesita el servidor. Con ella, el visor arranca igualmente desde la instantánea y pasa a la API en cuanto `/healthz` responde (ver `frontend/src/data/api.ts`).

`frontend/vercel.json` fija la caché: un año e inmutable para `/assets/` (ficheros con hash en el nombre) y una hora con revalidación para `/data/`.

## API y PostgreSQL en Render

`render.yaml` es un Blueprint de Render con:

- `oniel-postgres`: PostgreSQL 17, plan free, región Frankfurt.
- `oniel-api`: servicio web Docker (`backend/Dockerfile`, `rootDir: backend`), plan free, `healthCheckPath: /healthz`, `DATABASE_URL` enlazada a la base y `LOGFIRE_TOKEN` marcado `sync: false` (se aporta al aprobar el primer sync).
- `oniel-importer` (cron job, comentado): Render no ofrece cron jobs gratuitos y pide un método de pago en el workspace para crearlos. Para activarlo, añade un método de pago, descomenta el bloque y haz push.

Estado (8 de noviembre de 2026): Blueprint `oniel` (`exs-dbo9l3gu01pc73ekfu2g`) en el workspace "My Workspace" de la cuenta personal, creado desde el conector MCP de Render con `existingResources: create_new`, por lo que Render añadió el sufijo `-5e63` a los recursos: base `oniel-postgres-5e63` y API `oniel-api-5e63`, publicada en https://oniel-api-5e63.onrender.com. Con `autoSync` activo, cada push a `main` que cambie algo en `backend/` vuelve a desplegar la API; los que solo tocan `frontend/` o `docs/` no la despliegan, porque el servicio tiene `rootDir: backend` (comprobado el 12 de noviembre de 2026 en la lista de despliegues de Render). Los cambios del Blueprint se aplican con cada push.

Límites del plan gratuito, que conviene conocer:

- La API se suspende tras 15 minutos sin tráfico. Medido el 9 de noviembre de 2026: despertar costaba unos 75 s (61 s de `import all` y 11 s de arranque de Python); con `--if-changed` queda el arranque de Python más lo que Render tarde en levantar el contenedor. El visor no espera a la API: pinta la instantánea estática de Vercel al instante, la sondea en segundo plano (hasta dos minutos y medio) y cambia a ella cuando responde; mientras tanto la cabecera indica «despertando el servidor…» y la simulación espera a que esté lista.
- La base gratuita caduca a los 30 días de su creación (el 8 de diciembre de 2026). Todos los datos se regeneran con el importador a partir de los archivos del repositorio, así que no se pierde nada irrecuperable. Para una base persistente, cambia `plan: free` por `basic-256mb` en `render.yaml` (requiere método de pago) y haz push.

### Cargar o refrescar los datos

Sin cron job, la API carga los datos ella misma: con `ONIEL_IMPORT_ON_START=1` (fijado en `render.yaml`), `backend/docker-entrypoint.sh` ejecuta `oniel-data import all --if-changed` antes de arrancar el servidor. En Render la importación tarda alrededor de un minuto (en local, unos 5 segundos), así que solo se hace cuando cambia el commit desplegado (`RENDER_GIT_COMMIT`; fuera de Render, un hash de `data/` y `src/oniel/`): la huella de la última importación queda en la tabla `import_state` y los arranques tras una suspensión la encuentran igual y se la saltan. Si la base se recrea (la gratuita caduca a los 30 días), la tabla no existe y se importa de nuevo. Si más adelante se activa el cron job, basta con quitar esa variable.

También puede lanzarse desde cualquier máquina con `uv` y acceso a la base. La URL externa (External Database URL) está en el panel de la base en Render; no la guardes en el repositorio.

```bash
cd backend && ONIEL_DATABASE_URL='<External Database URL>' uv run oniel-data import all
```

La importación es repetible: crea el esquema si falta, sustituye los servicios de la fuente dentro de una transacción y registra la ejecución en `import_runs`. También regenera la instantánea estática de `frontend/public/data`, que conviene subir junto con los cambios.

`ONIEL_CORS_ORIGINS` debe incluir el dominio del visor (`["https://oniel.vercel.app"]` por defecto); los dominios de vista previa `*.vercel.app` se aceptan por expresión regular.

## Refresco automático del GTFS

`.github/workflows/gtfs.yml` descarga cada lunes el GTFS de Renfe y, si el horario ha cambiado, abre una PR con el fichero nuevo, `sources.json` y la instantánea regenerada. Qué hace paso a paso, cómo compara y qué queda manual (Ouigo) está en `docs/datos.md`, «Refresco de los horarios». Aquí va lo que toca al despliegue.

- **No publica nada.** El flujo abre la PR y lanza el CI sobre su rama; no fusiona. Al fusionarla una persona, Render reimporta la base (el commit toca `backend/`) y Vercel publica el visor con la instantánea nueva, como con cualquier PR de datos.
- **Permisos.** Usa solo el `GITHUB_TOKEN` de la ejecución, con `contents: write` (subir la rama), `pull-requests: write` (abrir la PR), `issues: write` (las etiquetas y las incidencias de aviso) y `actions: write` (lanzar el CI). No necesita ningún secreto.
- **Ajuste del repositorio.** Para que un flujo pueda abrir una PR hace falta marcar Settings → Actions → General → Workflow permissions → «Allow GitHub Actions to create and approve pull requests». Sin él, el paso «Abrir la PR» falla con «GitHub Actions is not permitted to create or approve pull requests». El flujo no aprueba ninguna PR.
- **El CI de esa PR.** GitHub retiene los flujos de `pull_request` cuando la PR la abre otro flujo con su token: hay que pulsar «Approve workflows to run» en la PR para que `Backend` y `Frontend` se ejecuten como comprobaciones suyas. Además, `ci.yml` admite `workflow_dispatch` y el refresco lo lanza sobre la rama; ese resultado queda en el commit y en la pestaña Actions, no en la lista de comprobaciones de la PR.
- **Base de datos.** El flujo importa en un PostgreSQL de servicio que desaparece al terminar, igual que el CI. No toca la base de Render.
- **Lo que crece.** Cada fichero de Renfe declarado alarga `import all` (unos 6 s en local; bastante más en el plan gratuito de Render, donde solo se ejecuta cuando cambia el commit desplegado). El flujo abre una PR cuando cambian los trenes o, como tarde, cada cuatro semanas; conviene retirar de vez en cuando los ficheros antiguos que no se quieran comparar.

## Logfire

Proyecto `oniel` en la organización personal `ebotiab` (región US): https://logfire-us.pydantic.dev/ebotiab/oniel

- Servicios: `oniel-api` (FastAPI + asyncpg) y `oniel-data` (importador y CLI).
- En local, el SDK lee `backend/.logfire/logfire_credentials.json` (no se versiona). Sin ese fichero ni `LOGFIRE_TOKEN` no se envía nada.
- En Render, definir `LOGFIRE_TOKEN` con un token de escritura del proyecto (Logfire → proyecto `oniel` → Settings → Write tokens).
- Comprobación: `uv run oniel-data logfire-test` envía una traza; las trazas de la API aparecen al usar cualquier endpoint.
- Las trazas no llevan cabeceras (`capture_headers=False`) ni datos de quien visita la web más allá de lo que la instrumentación de FastAPI anota por petición: ruta, estado, duración, agente de usuario y dirección de origen.

### Qué dicen las trazas de un despliegue

- **Versión.** En Render la versión del servicio (`service_version`) es el commit desplegado, que Render da en `RENDER_GIT_COMMIT`; en local es la del paquete (`0.1.0`). Las trazas anteriores al 12 de noviembre de 2026 llevan todas `0.1.0`. `/healthz` devuelve también el commit.
- **Arranque.** La API deja una traza `api started` cada vez que arranca: tras un despliegue y cada vez que Render la despierta.
- **Importación.** Cada `oniel-data import all` es un tramo `import all` del que cuelgan sus consultas, con `outcome` (`completed`, `skipped` cuando `--if-changed` no encuentra cambios, o `failed` con su excepción), la huella y los recuentos (líneas, ficheros de horarios, viajes). Como un tramo solo se envía al terminar, al empezar deja además un aviso `import all started`: uno sin tramo posterior es una importación en curso o interrumpida. La exportación de la instantánea es un tramo `export snapshot`.

### Consultar el estado: `oniel-data obs`

Desde `backend/`, solo lectura:

```bash
uv run oniel-data obs estado                              # qué corre en producción y cómo va
uv run oniel-data obs estado --commit <hash> --esperar 15 # espera hasta 15 min a que entre ese commit
uv run oniel-data obs consulta "select span_name, count(*) n from records group by 1 order by 2 desc" --horas 6
```

`obs estado` dice la versión desplegada y desde cuándo, la última importación y su resultado, los errores (nivel 17 o más) y las excepciones controladas desde que entró esa versión, las respuestas 4xx y 5xx por ruta y las rutas más lentas. Con `--commit` termina con código 1 si ese commit no es el de la API o su importación falló o no ha terminado, y `--esperar` repite la consulta cada 30 segundos hasta que entre: sustituye a sondear producción con `curl`. `--desde` cambia el inicio del periodo, `--json` da la salida para un programa. `obs consulta` ejecuta SQL sobre la tabla `records` y lo imprime en CSV; las columnas útiles son `service_name`, `service_version`, `deployment_environment` (`production`, `local`), `span_name`, `message`, `http_route`, `http_response_status_code`, `duration` (segundos), `level`, `is_exception`, `exception_type`, `exception_message`, `attributes`, `trace_id` y `start_timestamp`.

Una sesión de Claude tiene que ejecutarlo fuera del sandbox del shell, que corta la conexión TLS con Logfire. Cada traza del informe lleva su `trace_id`; se abre en https://logfire-us.pydantic.dev/ebotiab/oniel buscando `trace_id = '…'`.

### El token de lectura

`oniel-data obs` usa un token de **solo lectura** del proyecto, distinto del de escritura de Render. No está en el repositorio ni debe estarlo: se lee de la variable `LOGFIRE_READ_TOKEN` o, si no existe, del fichero `~/.config/oniel/logfire-read-token` (permisos 600) de la máquina de quien desarrolla. Sin token, las órdenes lo dicen y terminan sin fallar; el CI no lo tiene ni lo necesita, porque las pruebas simulan las respuestas.

Para renovarlo o darlo de alta en otra máquina: Logfire → proyecto `oniel` → Settings → Read tokens → crear uno, y guardarlo:

```bash
mkdir -p ~/.config/oniel && install -m 600 /dev/null ~/.config/oniel/logfire-read-token
pbpaste > ~/.config/oniel/logfire-read-token   # con el token en el portapapeles
```

El anterior se revoca en esa misma pantalla. Si Logfire responde 401, `obs estado` dice que el token fue rechazado: es la señal de que toca renovarlo.

### Acceso por MCP: no va en el repositorio

Logfire tiene un servidor MCP (`https://logfire-us.pydantic.dev/mcp`) que acepta el mismo token de lectura. Se estudió declararlo en un `.mcp.json` de proyecto el 12 de noviembre de 2026 y se descartó:

- Para no versionar el token, la cabecera tendría que salir de una variable (`${LOGFIRE_READ_TOKEN}`) o de una orden (`headersHelper`). La documentación de Claude Code no dice qué entorno ve la aplicación de escritorio al expandir variables (arrancada desde el Dock no hereda lo exportado en `~/.zshrc`), y con la variable sin definir el servidor se carga con el texto literal y falla.
- `headersHelper` sí podría leer el fichero, pero el repositorio es público: quien lo clone sin el token tendría en cada sesión un servidor que falla y una petición de aprobación de un servidor que no puede usar.
- En las sesiones en worktree de la aplicación de escritorio, `.mcp.json` se lee del checkout principal y no de la rama, y la aprobación de servidores de proyecto no está documentada allí; no se puede comprobar desde una PR.

La orden `oniel-data obs` cubre lo mismo con el token local y sin configuración. Quien quiera el MCP en su máquina puede declararlo a nivel de usuario, fuera del repositorio, con `claude mcp add --scope user --transport http` y un `headersHelper` que lea el fichero del token.

## Base de datos local

`docker-compose.yml` levanta PostgreSQL 17 en el puerto 5433 con usuario, contraseña y base `oniel`. El esquema se crea con `oniel-data db migrate`; las migraciones viven en `backend/src/oniel/db/migrations/`.
