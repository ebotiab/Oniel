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

- `VITE_LOGFIRE_TOKEN`: token público de la aplicación web `oniel-visor` de Logfire, solo en el entorno Production. Con él, el visor publicado envía sus errores a Logfire; sin él no envía nada ni descarga el SDK. Está puesta desde el 13 de noviembre de 2026, de tipo Config: Vercel no deja guardar como Secret una variable con el prefijo `VITE_` (el formulario la rechaza con «cannot use visibility: secret»), y no hace falta, porque el token es público. Cómo se dio de alta está en «Logfire», «Errores del visor».

El visor lee además dos variables que Vercel da a toda compilación, `VERCEL_ENV` (`production` o `preview`) y `VERCEL_GIT_COMMIT_SHA`; `frontend/vite.config.ts` las pasa al código. Necesitan que el proyecto tenga marcado Settings → Environment Variables → «Automatically expose System Environment Variables», que es el valor por defecto.

`frontend/vercel.json` fija la caché: un año e inmutable para `/assets/` (ficheros con hash en el nombre) y una hora con revalidación para `/data/`.

Las direcciones del visor son limpias (`/tramo/<id>`, `/glosario/<entrada>`) y las resuelve el propio visor, así que `frontend/vercel.json` lleva además una regla (`rewrites`) que sirve `index.html` para cualquier ruta que no sea un fichero. Deja fuera `/data/` y `/assets/`: un fichero de datos que no existe tiene que dar 404 y no la página del visor. Deja fuera también `/_vercel/`, de donde Vercel sirve el script que cuenta las visitas («Visitas del visor»). Los ficheros que existen (`/favicon.svg`, la instantánea) se sirven antes de mirar la regla. Tras tocarla conviene abrir en la vista previa de la PR una dirección profunda directamente y recargarla. En local, el servidor de desarrollo de Vite y `vite preview` hacen lo mismo sin configuración.

La compilación guarda cada ficha como `<ruta>.html`; tanto `vite preview` como Vercel (con `cleanUrls`) la sirven al abrir la dirección sin extensión. Hay una página HTML por vista principal (`/linea/<id>`, `/tramo/<id>`, `/nodo/<id>`, `/cobertura`…) con su título, descripción, dirección canónica y etiquetas para compartir. La portada también contiene enlaces a todas las líneas de la instantánea. Con JavaScript desactivado, la descripción y los enlaces se pueden leer y recorrer desde el primer HTML.

Con JavaScript activo, ese mismo HTML muestra la cabecera y el panel con «Cargando la red…» mientras llega el módulo. Antes se veía la página de lectura entera hasta que React la sustituía. Se reprodujo en la portada y en una estación reteniendo el módulo, con el CSS y Archivo ya cargados y sin API. Al llegar `DOMContentLoaded`, si el módulo ha fallado, se recupera la lectura. Si ya ha solicitado el montaje, el panel se conserva hasta el primer pintado de React. La instantánea y el mapa siguen cargándose por separado. [Capturas antes y después en escritorio y móvil](capturas/arranque/).

De esa misma lista de páginas se genera `/sitemap.xml` con las direcciones de producción. Las simulaciones y las comparaciones elegidas por el visitante quedan fuera. El fichero `/robots.txt` anuncia el sitemap. Ambas direcciones están excluidas de la regla del visor. Al publicar, se puede comprobar el contenido con `curl -fsS https://oniel.vercel.app/robots.txt` y `curl -fsS https://oniel.vercel.app/sitemap.xml`. En Google Search Console, la propiedad con prefijo `https://oniel.vercel.app/` permite enviar el sitemap e inspeccionar el estado de la portada o de una ficha.

### Visitas del visor

Desde el 18 de noviembre de 2026 el visor publicado cuenta sus visitas con Vercel Web Analytics (`@vercel/analytics` 2.0.1), para saber si se usa y qué se consulta. El código está en `frontend/src/telemetria/visitas.ts`. Hasta entonces lo único que quedaba de una visita eran las peticiones a la API en Logfire, que no distinguen a un visitante de otro, no dicen de dónde llega y no existen si quien visita se va antes de que Render despierte la API.

**Dónde se mira.** Vercel → proyecto `oniel` → Analytics (https://vercel.com/enrique-botia-barbera-s-projects/oniel/analytics): visitantes y páginas vistas por día, qué páginas, de dónde se llega, país, dispositivo, sistema y navegador.

**Qué se envía.** Una petición a `/_vercel/insights/view`, en el propio dominio del visor, por cada página vista: al abrir el visor y cada vez que cambia la ruta (una línea, un tramo, una estación, el glosario). Lleva la dirección sin parámetros ni fragmento, que el visor recorta antes de enviar (`alEnviar`), y, en la primera página, la página desde la que se llega si es de otro sitio. Vercel anota además la hora, la ubicación aproximada (país, región y ciudad), el sistema, el navegador y el tipo de dispositivo. Según su documentación (https://vercel.com/docs/analytics/privacy-policy, consultada el 18 de noviembre de 2026), no usa cookies de terceros, distingue a un visitante por un resumen calculado de la petición que se descarta a las 24 horas, y los datos no quedan asociados a una persona ni a una dirección IP. El script no escribe nada en el navegador de quien visita, y el visor no envía eventos propios: solo páginas vistas.

**Qué no se cuenta.**

- El servidor de desarrollo, las pruebas y las vistas previas de Vercel: como con los errores, hace falta una compilación de producción con `VERCEL_ENV=production`, y sin ella el recuento no forma parte de lo publicado.
- Los navegadores automáticos: el script de Vercel no envía nada si el navegador se declara automatizado (`navigator.webdriver`, como Playwright) o lleva `Headless` en su agente de usuario.
- El navegador integrado de la app de Claude, con el que las sesiones de desarrollo abren producción (`Claude/` en el agente de usuario).
- Un navegador marcado. Abrir https://oniel.vercel.app/?visitas=no deja de contar las visitas de ese navegador, y https://oniel.vercel.app/?visitas=si vuelve a contarlas. El parámetro desaparece de la dirección al momento, y esa es la señal de que se ha aplicado. La marca se guarda en ese navegador (`localStorage`, clave `oniel:visitas:no-contar`): hay que ponerla una vez en cada navegador y en cada dispositivo de quien mantiene Oniel, no dura en una ventana privada y se pierde al borrar los datos del sitio.
- Las visitas con un bloqueador de contenido que corte el script: el visor funciona igual y el recuento se queda corto.

**Cuota.** El plan Hobby incluye 50.000 páginas vistas al mes, sumando todos los proyectos de la cuenta, y guarda un mes de datos. Al superarlas Vercel deja de recoger hasta el ciclo siguiente y no cobra nada (https://vercel.com/docs/analytics/limits-and-pricing, consultada el 18 de noviembre de 2026).

**Peso.** Medido el 18 de noviembre de 2026: el arranque del visor publicado crece 2,5 kB (1,1 kB comprimido). El script de Vercel se pide aparte y sin retrasar el primer pintado (`defer`). Fuera de producción, lo compilado no lleva nada del recuento.

**Alta, hecha el 18 de noviembre de 2026.** Web Analytics se activa por proyecto, y el script solo existe en los despliegues posteriores:

1. Activarlo: `env -u HTTPS_PROXY -u HTTP_PROXY vercel project web-analytics enable oniel --scope enrique-botia-barbera-s-projects`, o en la web, Vercel → proyecto `oniel` → Analytics → Enable.
2. Volver a desplegar producción con una fusión que toque `frontend/`.
3. Comprobarlo: `curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://oniel.vercel.app/_vercel/insights/script.js` tiene que dar `200` y JavaScript, y al abrir el visor en un navegador sin marcar, la pestaña de red enseña un `POST` a `/_vercel/insights/view`. Las visitas aparecen después en el panel.

Sin activar, Vercel no sirve el script. Antes de este cambio la regla de `rewrites` devolvía `index.html` en su lugar (comprobado en producción el 18 de noviembre de 2026: `200 text/html`), y un navegador que lo cargara como script habría dejado un error de sintaxis en Logfire en cada visita. Por eso la regla deja fuera `/_vercel/`: si el recuento se desactiva algún día, el script da 404 y el visor sigue igual.

## API en Render

`render.yaml` es un Blueprint de Render con:

- `oniel-api`: servicio web Docker (`backend/Dockerfile`, `rootDir: backend`), plan free, `healthCheckPath: /healthz`, `DATABASE_URL` y `LOGFIRE_TOKEN` marcados `sync: false` (se escriben en el panel de Render; un sync posterior no los toca).
- `oniel-importer` (cron job, comentado): Render no ofrece cron jobs gratuitos y pide un método de pago en el workspace para crearlos. Para activarlo, añade un método de pago, descomenta el bloque y haz push.

Estado (8 de noviembre de 2026): Blueprint `oniel` (`exs-dbo9l3gu01pc73ekfu2g`) en el workspace "My Workspace" de la cuenta personal, creado desde el conector MCP de Render con `existingResources: create_new`, por lo que Render añadió el sufijo `-5e63` a los recursos: base `oniel-postgres-5e63` y API `oniel-api-5e63`, publicada en https://oniel-api-5e63.onrender.com. Con `autoSync` activo, cada push a `main` que cambie algo en `backend/` vuelve a desplegar la API; los que solo tocan `frontend/` o `docs/` no la despliegan, porque el servicio tiene `rootDir: backend` (comprobado el 12 de noviembre de 2026 en la lista de despliegues de Render). Los cambios del Blueprint se aplican con cada push.

Límites del plan gratuito, que conviene conocer:

- La API se suspende tras 15 minutos sin tráfico. Medido el 9 de noviembre de 2026: despertar costaba unos 75 s (61 s de `import all` y 11 s de arranque de Python); con `--if-changed` queda el arranque de Python más lo que Render tarde en levantar el contenedor. El visor no espera a la API: pinta la instantánea estática de Vercel al instante, la sondea en segundo plano (hasta dos minutos y medio) y cambia a ella cuando responde; mientras tanto la cabecera indica «despertando el servidor…» y la simulación espera a que esté lista. Para que no se duerma en horario de día hay un flujo de GitHub Actions, apagado por defecto: «Mantener la API despierta», más abajo.
- La base de datos ya no está en Render: su PostgreSQL gratuito caduca a los 30 días de crearse (el de Oniel, `oniel-postgres-5e63`, el 8 de diciembre de 2026) y se borra catorce días después. Ver «Base de datos», más abajo.

### Base de datos

La API se conecta a un PostgreSQL externo que no caduca, en el plan gratuito de Neon (https://neon.tech), región de Fráncfort (`aws-eu-central-1`), la misma zona que la API. Nada de lo que guarda es irrecuperable: todo se regenera con el importador a partir de los ficheros del repositorio, así que no hacen falta copias de seguridad ni migrar datos de una base a otra. Una base vacía se llena sola en el primer despliegue.

Cómo se conecta:

- `DATABASE_URL` se escribe a mano en el panel de Render (servicio `oniel-api-5e63`, «Environment»). No está en el repositorio ni en ningún fichero: lleva la contraseña.
- Se usa la cadena de conexión **directa**, no la del pooler (en Neon, «Connection pooling» desactivado al copiarla; el servidor no lleva `-pooler` en el nombre). El pooler reparte las conexiones por transacción y asyncpg prepara sentencias por conexión.
- La cadena de Neon trae `sslmode=require`, que asyncpg entiende, y `channel_binding=require`, que no: `oniel.db.pool.normalize_dsn` lo quita antes de conectar, así que se puede pegar tal cual.
- Neon suspende la base a los cinco minutos sin actividad y la despierta en la primera conexión, en torno a un segundo. El pool cierra las conexiones que llevan dos minutos sin uso para no guardar una que la base ya cortó.

Límites del plan gratuito de Neon que importan aquí: 0,5 GB de almacenamiento (la base de Oniel ocupa menos de 100 MB con 25 líneas) y un cupo mensual de horas de cómputo, que la suspensión automática mantiene lejos.

Para cambiar de base (otro proveedor, o una nueva de Neon): se crea la base vacía, se pega su cadena en `DATABASE_URL` en Render y se lanza un despliegue («Manual Deploy»). El arranque aplica las migraciones e importa los datos; `uv run oniel-data obs estado` dice cuándo ha terminado.

### Cargar o refrescar los datos

Sin cron job, la API carga los datos ella misma: con `ONIEL_IMPORT_ON_START=1` (fijado en `render.yaml`), `backend/docker-entrypoint.sh` ejecuta `oniel-data import all --if-changed --no-snapshot` antes de arrancar el servidor. En Render la importación tarda minutos (en local, unos 15 segundos), así que solo se hace cuando cambia el commit desplegado (`RENDER_GIT_COMMIT`; fuera de Render, un hash de `data/` y `src/oniel/`): la huella de la última importación queda en la tabla `import_state` y los arranques tras una suspensión la encuentran igual y se la saltan. Si la base se recrea (la gratuita caduca a los 30 días), la tabla no existe y se importa de nuevo. Si más adelante se activa el cron job, basta con quitar esa variable.

También puede lanzarse desde cualquier máquina con `uv` y acceso a la base. La URL externa (External Database URL) está en el panel de la base en Render; no la guardes en el repositorio.

```bash
cd backend && ONIEL_DATABASE_URL='<External Database URL>' uv run oniel-data import all
```

La red, los horarios, el registro de ejecuciones y la huella se confirman juntos en PostgreSQL. Si la importación se interrumpe, la base conserva los datos y la huella anteriores. Al reintentar se vuelve a cargar el cambio pendiente. Si arrancan dos importaciones a la vez, la segunda espera a la primera antes de comparar la huella.

En local la orden también regenera la instantánea de `frontend/public/data`. Si falla al escribir los ficheros, corrige la causa y repite `oniel-data import all` antes de subirlos.

**Cuánto tarda y por qué importa.** Render da por fallido («Timed Out») un despliegue que no responde en unos 15 minutos, y la API no responde hasta que la importación termina. El 15 de noviembre de 2026, con 25 líneas y tres ficheros de horarios, tardó 474 s en producción (commit `0f4f589`): unos 35 s las 25 redes, 129 s y 136 s los dos ficheros de Renfe, 4 s el de Ouigo y 166 s la exportación de la instantánea. Desde el 17 de noviembre de 2026 hace menos trabajo, con el mismo resultado en la base:

- **El arranque de producción no exporta la instantánea** (`--no-snapshot`). La instantánea que ve el visitante la sirve Vercel desde `frontend/public/data` del repositorio; la que exportaba el contenedor de la API se quedaba en su disco y no la leía nadie. Eran 2.600 consultas, un tercio del tiempo. En local y en el CI `import all` la sigue exportando, que es como se regenera.
- **Las filas van por lotes.** Los trenes de un fichero se guardan con una copia por tabla (`copy_records_to_table` en `services`, `service_dates`, `service_stops` y `service_segment_passes`) en vez de cuatro sentencias por tren, y las fuentes, los nodos, los tramos y las paradas de cada línea, con una sentencia agrupada por tabla (`executemany`). Un fichero de Renfe pasa de unas 14.000 idas y vueltas a la base a 62, y las 25 redes, de 5.700 a 520. Con la base fuera de Render (véase «Base de datos») cada ida y vuelta cuesta más que antes, así que esto es lo que más pesa.

Medido en local el 17 de noviembre de 2026, la misma importación: de 69 s a 37 s con la instantánea, y 16 s sin ella (3 s las redes, 6 s cada fichero de Renfe); la instantánea exportada es idéntica byte a byte. Lo que queda es sobre todo cálculo (trazar cada línea y resolver el paso de cada tren por cada tramo), que en el plan gratuito de Render va varias veces más lento que en local. La duración real de cada importación está en Logfire: `uv run oniel-data obs estado` la enseña, y los tramos `import network`, `import gtfs` y `export snapshot` dicen en qué se fue.

Los dos ficheros de Renfe se importan a propósito: el segundo no sustituye al primero, porque la ficha de una estación o de un tramo compara los trenes de un horario con los del siguiente (`docs/datos.md`, «Evolución del servicio»), y la API responde esa comparación desde la base. Cada fichero más de Renfe añade lo que tarde en resolverse; retirar uno antiguo de `feeds` lo quita.

Una prueba (`tests/test_importing.py`) cuenta las idas y vueltas de una importación completa y falla si alguien vuelve a escribir fila a fila.

`ONIEL_CORS_ORIGINS` debe incluir el dominio del visor (`["https://oniel.vercel.app"]` por defecto); los dominios de vista previa `*.vercel.app` se aceptan por expresión regular.

### Lo que la API guarda en memoria

La red y los horarios solo cambian al importar, pero cada petición volvía a leerlos: abrir una línea eran diez consultas seguidas, dos de ellas sobre los horarios de toda la red (el día de referencia y los pasos por tramo). Desde el 18 de noviembre de 2026 la API guarda en memoria lo que lee (`oniel.repo.cache`) y lo reutiliza mientras los datos sean los mismos.

- **Cómo sabe que son los mismos.** La base lleva una versión de los datos, un número en la tabla `data_version` que sube una vez por cada transacción que escribe en una tabla de la red o de los horarios (migración `0014_version_de_datos`, con un disparador por sentencia en cada tabla). La API la lee al empezar cada petición: si no ha cambiado, usa lo guardado; si ha cambiado, lo tira todo y vuelve a leer. No se supone nada sobre cuándo se importa: una importación lanzada a mano con la API en marcha se ve en la petición siguiente.
- **Qué guarda.** Las líneas, los nodos, los tramos con su geometría, las conexiones, las anotaciones, las fuentes, los operadores, el día de referencia, el índice ligero ya simplificado, la cobertura, el grafo de rutas y, por cada día pedido, los pasos por tramo y los tramos sin otro camino. Como mucho 128 entradas; al llenarse sale la que lleva más tiempo sin usarse, así que pedir muchos días distintos no hace crecer la memoria.
- **Qué no.** Lo que depende de un tramo o de una estación y de un día (los trenes de un tramo, las paradas de una estación, la evolución del servicio) se sigue leyendo en cada petición, con sus índices.
- **Una tabla nueva** que la API lea tiene que llevar los dos disparadores (`data_version_write` y `data_version_truncate`) en su migración; una prueba de `tests/test_integration_db.py` falla si a alguna le faltan.
- **Fuera de una petición** (la importación, la exportación de la instantánea) no se guarda nada.

Medido en local el 18 de noviembre de 2026, con 30 líneas y la API ya caliente: `/api/lines/{line_id}` pasa de 105 ms y 10 consultas a 3 ms y una (la de la versión); `/api/lines`, de 115 ms a 5 ms; `/api/coverage`, de 75 ms a 4 ms; `/api/segments/{segment_id}/services`, de 62 ms a 19 ms. La primera petición tras arrancar o tras una importación sigue pagando las lecturas. Las respuestas son idénticas byte a byte. Las consultas que quedan usan sus índices (`EXPLAIN ANALYZE`): no hizo falta ninguno nuevo. En producción la diferencia es mayor, porque allí cada consulta cuesta además el viaje a la base y, tras un rato sin tráfico, la de los pasos por tramo de toda la red tardaba más de un segundo.

`/api/alternatives` es el cálculo más largo (unos 5 s en local para un día; `docs/simulacion.md`, «Tramos sin alternativa», «Lo que tarda»). El visor lee el del día de referencia de la instantánea; el de otro día se calcula la primera vez que se pide y queda guardado. Es cálculo puro, sin esperas, y se lanza en otro hilo (`asyncio.to_thread`, en `network_repo`), de uno en uno: si llegan dos peticiones del mismo día, la segunda espera a la primera y lo encuentra hecho.

Hasta el 23 de noviembre de 2026 corría dentro del bucle de la API y tardaba minutos (#262): mientras duraba, la API no contestaba a nada, tampoco a `/healthz`, y Render daba la instancia por caída y la reiniciaba. Una sola petición de otro día bastaba. No era la memoria: el día del fallo (22 de noviembre) el proceso usaba 93 MB de los 512 del plan, y el evento de Render dice «HTTP health check failed (timed out after 5 seconds)». De ahí la regla para cualquier cálculo largo de la API: fuera del bucle, y medido. En local, con el cálculo en marcha, `/healthz` contesta en menos de 0,1 s. En producción, el 23 de noviembre de 2026 y ya con el arreglo desplegado, la primera petición de otro día tardó 16,7 s y la segunda, 0,3 s; `/healthz` contestó las 60 veces que se le pidió mientras tanto (la más lenta, en 0,33 s) y la API no se reinició.

### Mantener la API despierta

El visor no espera a la API, pero quien llega por un enlace directo a una comparación o a una simulación sí espera a que despierte (cerca de un minuto). `.github/workflows/mantener-api-despierta.yml` lo evita en horario de día: pide `/healthz` cada 10 minutos, y así la API no llega a los 15 minutos sin tráfico que la suspenden. **Está apagado por defecto.**

- **Encender y apagar.** En GitHub, Settings → Secrets and variables → Actions → pestaña Variables, la variable del repositorio `ONIEL_MANTENER_API_DESPIERTA`: con valor `1` el flujo pide `/healthz`; con cualquier otro valor, o sin la variable, cada ejecución programada se salta el trabajo y no hace ninguna petición (en la pestaña Actions aparece como «skipped»). No hace falta tocar código. Para probarlo a mano: Actions → «Mantener la API despierta» → «Run workflow», o `gh workflow run mantener-api-despierta.yml`. La dirección de la API está en el flujo; una variable `ONIEL_API_URL` la sustituye si algún día cambia.
- **Horario.** Cron `3-59/10 5-22 * * *`, en UTC: GitHub no sabe de cambios de hora, así que la franja cubre las dos. En invierno (UTC+1) va de 06:00 a 23:59 en Madrid; en verano (UTC+2), de 07:00 a 00:59. La API sigue despierta hasta 15 minutos después de la última petición.
- **Una petición por ejecución.** `curl` con 150 s de tiempo máximo por intento, por si la encuentra dormida (Render retiene la petición mientras la despierta), y dos reintentos ante cualquier fallo; el flujo falla solo si ninguno de los tres intentos responde. Sin permisos sobre el repositorio (`permissions: {}`) y con un tope de 10 minutos.
- **No toca la base de datos.** `/healthz` responde con la versión y el commit desplegado, sin consultas (`backend/src/oniel/api/main.py`): la conexión por petición y la lectura de `data_version` solo las piden las rutas de `/api` (`oniel.api.deps.get_connection`). El pool cierra las conexiones que llevan dos minutos sin uso, así que con solo estas peticiones Neon sigue suspendiéndose a los cinco minutos y no gasta horas de cómputo. La API sí conecta con la base al arrancar (el pool abre una conexión y `import all --if-changed` mira `import_state`), pero eso pasa una vez por despertar y, con el flujo encendido, hay menos despertares, no más.
- **No deja trazas en Logfire.** La instrumentación de FastAPI excluye `/healthz` (`EXCLUDED_URLS` en `backend/src/oniel/observability.py`; lo comprueba `tests/test_observability.py`). Lo que sí aumenta es lo que la API envía por estar despierta más tiempo: las métricas del sistema, 4 puntos por minuto (unas 4.400 al día con 18 horas despierta, unas 135.000 al mes), dentro de los 10 millones mensuales del plan (véase «Volumen y cuota»).
- **Horas de Render.** El plan gratuito da 750 horas de instancia al mes por workspace, compartidas por todos sus servicios web gratuitos; una instancia suspendida no las gasta, y si se acaban, Render suspende todos los servicios gratuitos del workspace hasta el mes siguiente (https://render.com/docs/free, «Free instance hours», consultado el 19 de noviembre de 2026). Con el flujo encendido la API queda despierta unas 18 horas y cuarto al día: unas 550 horas en un mes de 30 días y 566 en uno de 31. Quedan unas 180 horas para las visitas fuera de esa franja y para cualquier otro servicio gratuito del workspace; hoy `oniel-api-5e63` es el único servicio web.
- **Minutos de GitHub Actions.** El repositorio es público y sus ejecuciones no gastan minutos. Son unas 108 al día.
- **Sin garantías de puntualidad.** GitHub avisa de que el evento `schedule` puede retrasarse cuando hay mucha carga y de que, con carga suficiente, algunas ejecuciones en cola se descartan; un hueco de más de 15 minutos deja dormir a la API hasta la siguiente. Además, en un repositorio público los flujos programados se desactivan solos tras 60 días sin actividad en el repositorio; se vuelven a activar en la pestaña Actions («Enable workflow»). Fuente: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows, evento `schedule` (consultado el 19 de noviembre de 2026).

## Refresco automático del GTFS

`.github/workflows/gtfs.yml` descarga cada lunes el GTFS de Renfe y, si el horario ha cambiado, abre una PR con el fichero nuevo, `sources.json` y la instantánea regenerada. Qué hace paso a paso, cómo compara y qué queda manual (Ouigo) está en `docs/datos.md`, «Refresco de los horarios». Aquí va lo que toca al despliegue.

- **No publica nada.** El flujo abre la PR y lanza el CI sobre su rama; no fusiona. Al fusionarla una persona, Render reimporta la base (el commit toca `backend/`) y Vercel publica el visor con la instantánea nueva, como con cualquier PR de datos.
- **Permisos.** Usa solo el `GITHUB_TOKEN` de la ejecución, con `contents: write` (subir la rama), `pull-requests: write` (abrir la PR), `issues: write` (las etiquetas y las incidencias de aviso) y `actions: write` (lanzar el CI). No necesita ningún secreto.
- **Ajuste del repositorio.** Para que un flujo pueda abrir una PR hace falta marcar Settings → Actions → General → Workflow permissions → «Allow GitHub Actions to create and approve pull requests». Sin él, el paso «Abrir la PR» falla con «GitHub Actions is not permitted to create or approve pull requests». El flujo no aprueba ninguna PR.
- **El CI de esa PR.** GitHub retiene los flujos de `pull_request` cuando la PR la abre otro flujo con su token: hay que pulsar «Approve workflows to run» en la PR para que `Backend` y `Frontend` se ejecuten como comprobaciones suyas. Además, `ci.yml` admite `workflow_dispatch` y el refresco lo lanza sobre la rama; ese resultado queda en el commit y en la pestaña Actions, no en la lista de comprobaciones de la PR.
- **Base de datos.** El flujo importa en un PostgreSQL de servicio que desaparece al terminar, igual que el CI. No toca la base de Render.
- **Lo que crece.** Cada fichero de Renfe declarado alarga `import all` (unos 6 s en local; varias veces más en el plan gratuito de Render, donde solo se ejecuta cuando cambia el commit desplegado; véase «Cargar o refrescar los datos»). El flujo abre una PR cuando cambian los trenes o, como tarde, cada cuatro semanas; conviene retirar de vez en cuando los ficheros antiguos que no se quieran comparar.

## Logfire

Proyecto `oniel` en la organización personal `ebotiab` (región US): https://logfire-us.pydantic.dev/ebotiab/oniel

- Servicios: `oniel-api` (FastAPI + asyncpg), `oniel-data` (importador y CLI) y `oniel-visor` (los errores del navegador; «Errores del visor», más abajo).
- En local, el SDK lee `backend/.logfire/logfire_credentials.json` (no se versiona). Sin ese fichero ni `LOGFIRE_TOKEN` no se envía nada.
- En Render, definir `LOGFIRE_TOKEN` con un token de escritura del proyecto (Logfire → proyecto `oniel` → Settings → Write tokens).
- Comprobación: `uv run oniel-data logfire-test` envía una traza; las trazas de la API aparecen al usar cualquier endpoint.
- Las trazas no llevan cabeceras (`capture_headers=False`) ni datos de quien visita la web más allá de lo que la instrumentación de FastAPI anota por petición: ruta, estado, duración, agente de usuario y dirección de origen.
- La API no continúa la traza de quien la llama aunque la petición traiga una cabecera `traceparent` (`distributed_tracing=False`): es lo que Logfire recomienda para un servicio abierto a internet.
- Toda la configuración está en `backend/src/oniel/observability.py`.

### Entornos

Cada registro lleva su entorno en `deployment_environment`, que en el backend sale de `ONIEL_ENVIRONMENT` y en el visor, de `VERCEL_ENV`. Hay dos y no se crean más sin motivo:

| Entorno | Quién lo envía | Cuándo |
|---|---|---|
| `production` | La API y el importador en Render (`render.yaml` fija `ONIEL_ENVIRONMENT=production`) | Siempre |
| `production` | El visor publicado en https://oniel.vercel.app (`VERCEL_ENV=production`) | Solo cuando hay un error, y solo si Vercel tiene `VITE_LOGFIRE_TOKEN` |
| `local` | Quien desarrolla, desde su máquina | Solo si tiene credenciales de escritura (`backend/.logfire/` o `LOGFIRE_TOKEN`). Las sesiones en worktree no las tienen y no envían nada: desde el 9 de noviembre de 2026 no llega nada de `local` |

- **Las pruebas no envían nunca.** Bajo pytest la configuración fuerza `send_to_logfire=False`, haya o no un token en el entorno (`observability.send_to_logfire`); las pruebas que miran tramos usan `capfire`, que los guarda en memoria. El plugin de pytest de Logfire, que se activa solo cuando hay `CI=true` y `LOGFIRE_TOKEN`, está desactivado con `--no-logfire` en `backend/pyproject.toml`. No hay entorno `ci` ni `test`: el CI no tiene token ni lo necesita.
- **No hay entorno `preview`.** Las vistas previas de Vercel son solo el visor y hablan con la API de producción: sus peticiones son tráfico de `production`. Sus errores de navegador no se envían: el visor solo inicializa Logfire cuando `VERCEL_ENV` es `production`, y el token está definido solo en ese entorno de Vercel. Una vista previa la abre quien revisa la PR, con la consola delante; enviarla gastaría cuota y, de ir como producción, abriría incidencias y correos por código sin fusionar.
- **El visor en local y en las pruebas no envía nunca.** El servidor de desarrollo no es una compilación de producción y no tiene token. Playwright compila aparte un visor con un token de mentira y responde él mismo a lo que envía (`frontend/e2e/telemetria.spec.ts`).
- Una importación lanzada a mano desde una máquina contra la base de Render sale como `local` salvo que se le ponga `ONIEL_ENVIRONMENT=production`.
- En la web de Logfire el entorno se elige en el selector que hay bajo el del proyecto; en `oniel-data obs`, con `--entorno`.

### Volumen y cuota

El plan personal incluye 10 millones de registros al mes, contando juntos tramos, avisos y puntos de métricas, y conserva los datos 30 días. No cobra por pasarse: al superar lo incluido dejan de abrirse la vista en vivo y el detalle de las trazas (las consultas siguen funcionando), y algo más allá lo nuevo deja de guardarse hasta que el mes se reinicia. El consumo se ve en Logfire → ajustes de la organización → Billing & usage.

Medido el 12 de noviembre de 2026, en 24 horas producción envió unos 140.000 registros (a ese ritmo, 4,2 millones al mes): 129.000 eran sentencias `INSERT` sueltas del importador y 7.700 comprobaciones de salud de Render; las peticiones de visitantes eran unos cientos. Desde la PR de #124 se envía solo lo que dice algo:

| Qué | Antes | Ahora |
|---|---|---|
| Una importación completa (seis líneas, tres ficheros de horarios) | 9.610 registros, 9.588 de ellos sentencias SQL | 23 registros: `import all started`, `import all`, un tramo y un aviso por línea y por fichero de horarios, las anotaciones y `export snapshot` |
| `GET /healthz` de Render | Unos 7.700 tramos al día, más sus métricas HTTP | Nada: la ruta está excluida de la instrumentación (`EXCLUDED_URLS`) |
| Métricas del sistema | No había | 4 puntos por minuto y proceso: 5.760 al día como mucho, si la API no llega a suspenderse |

- **El importador no traza SQL.** `instrument_asyncpg` solo se activa en la API (`configure_logfire(..., sql=True)`), donde una petición hace pocas consultas y verlas explica una ruta lenta. Lo que interesa de una importación lo llevan sus tramos, con recuentos y resultado. Quien añada una fase a la importación le pone su tramo; no hay que volver a instrumentar la base.
- **Las cifras se sacaron sin enviar nada**, contando en memoria los tramos de un `oniel-data import all` en local antes y después del cambio.
- Si el volumen vuelve a crecer, el panel estándar «Usage Overview» de Logfire (Dashboards → + Dashboard → Logfire) lo desglosa por servicio y por nombre de tramo, y esta consulta da lo mismo: `uv run oniel-data obs consulta "select service_name, span_name, count(*) n from records group by 1, 2 order by 3 desc" --horas 24`.

### Métricas del sistema

`logfire.instrument_system_metrics` (extra `system-metrics`, que trae `psutil`) envía cuatro métricas, una lectura por minuto de cada una (`SYSTEM_METRICS` en `observability.py`):

| Métrica | Qué dice |
|---|---|
| `process.memory.usage` | Memoria residente del proceso, en bytes. Es la que cuenta contra los 512 MB de la instancia gratuita de Render |
| `process.cpu.utilization` | Fracción de un núcleo que usa el proceso (1 = un núcleo entero) |
| `system.memory.utilization` (`state = available`) | Fracción de memoria disponible en la máquina. En Render es la de la máquina anfitriona, no la del contenedor: sirve de contexto, no de límite |
| `system.cpu.simple_utilization` | Fracción de procesador ocupada en la máquina entera |

Las envían los dos servicios. La importación dura un par de minutos, así que `docker-entrypoint.sh` la lanza con `OTEL_METRIC_EXPORT_INTERVAL=10000` (una lectura cada 10 segundos) para que se vea cómo crece su memoria; la API usa el minuto por defecto. Se miran en Logfire → Metrics explorer o Hosts, o con SQL sobre la tabla `metrics`:

```bash
uv run oniel-data obs consulta "select service_name, metric_name, count(*) n, round(max(scalar_value)) maximo from metrics where metric_name like 'process.%' group by 1, 2" --horas 24
```

No se usa `base='full'`: añade cientos de puntos por minuto (procesador por núcleo y modo, discos, red) que aquí no dicen nada.

### Errores agrupados

Logfire agrupa las excepciones repetidas en incidencias y avisa cuando aparece una nueva o se reabre una resuelta (la función se llama «Error tracking»; antes, «Issues»). Necesita que el fallo llegue como excepción, no como un aviso de nivel error, y así llegan los de Oniel: una excepción no controlada en la API queda en el tramo de la petición con su traza (`is_exception`, nivel 17) y una importación que falla, en el tramo `import all` con `outcome = failed`. Lo comprueban `tests/test_observability.py` y `tests/test_importing.py`. Los `HTTPException` (404, 422) quedan como excepciones de nivel aviso: son respuestas correctas, no errores del servidor.

Está activado en el proyecto `oniel` desde el 12 de noviembre de 2026, con aviso al canal «Correo» y solo para producción: el filtro `deployment_environment = 'production'` (Advanced options) deja fuera las excepciones que alguien envíe desde `local`. Se configura en la web de Logfire: barra lateral → Product & Behavior → Error tracking → Configure (canales y filtros). Las incidencias tardan unos minutos en aparecer. Desactivarlo borra las incidencias acumuladas.

### Errores del visor

Desde #131 el visor publicado envía a Logfire sus errores, y solo sus errores, con `@pydantic/logfire-browser` (0.35.1, en beta: antes de subir de versión hay que releer su documentación, https://pydantic.dev/docs/logfire/instrument/typescript/packages/browser/). El código está en `frontend/src/telemetria/`.

**Qué se envía.** Un registro por cada excepción no controlada (`Uncaught error`) y por cada promesa rechazada que nadie atiende (`Unhandled promise rejection`), de nivel error y con forma de excepción, que es lo que «Errores agrupados» necesita. React pasa por ahí los fallos al pintar un componente. Cada registro lleva:

| Atributo | Qué es |
|---|---|
| `exception.message`, `exception.stacktrace` | El mensaje del error y su traza, con los nombres del código compilado (no se publican mapas de código) |
| `logfire.exception.fingerprint` | La huella con la que «Errores agrupados» junta las repeticiones de un mismo error. Sale de la traza del código compilado, así que un mismo fallo puede abrir una incidencia nueva tras otro despliegue |
| `logfire.page.url.path` | La ruta del visor en la que ocurrió (`/tramo/<id>`), sin parámetros ni fragmento. Lo añade Oniel |
| `service.version` | El commit que compiló Vercel |
| `deployment.environment.name` | `production` |
| `browser.language`, `browser.brands`, `browser.mobile`, `browser.platform` | Idioma, navegador con su versión mayor, si es móvil y sistema operativo. En los navegadores que no dan esos datos (Firefox, Safari), el agente de usuario entero en `user_agent.original`. Los anota el SDK |
| `telemetry.sdk.*` | Nombre y versión del SDK |

**Qué no se envía.** A Logfire, nada en una visita sin errores: ni carga de página, ni rendimiento, ni peticiones, ni clics. El recuento de visitas es aparte y va a Vercel («Visitas del visor»). No hay repetición de sesión (el paquete que la hace no está instalado), ni identificador de sesión o de visitante, ni se guarda nada en el navegador (`rum.session: false`). No va el contenido de ningún campo: lo que se escribe en el buscador o en el filtro del glosario no está en la dirección ni en los mensajes de error. Tampoco se instrumentan `fetch` ni los clics (`autoInstrumentations: false`): de hacerlo, cada sondeo de `/healthz` sin respuesta mientras Render despierta la API llegaría como un error, y los fallos de la API ya los envía la propia API. Un recurso que no carga (una tesela, una imagen) no es un error de JavaScript y no llega. Como en cualquier petición, Logfire ve la dirección IP de quien la hace y el origen `https://oniel.vercel.app`; el visor no las anota.

**Cuándo.** Solo si las tres condiciones se cumplen al compilar: compilación de producción, `VERCEL_ENV=production` y `VITE_LOGFIRE_TOKEN` definido (`frontend/src/telemetria/arranque.ts`). Si falta alguna, el SDK no forma parte de lo publicado y el visor no hace ninguna petición a Logfire.

**Token.** El visor envía directamente a `https://logfire-us.pydantic.dev/v1/traces` con el token de una «aplicación web» (frontend application) de Logfire. Ese token es público por diseño, queda a la vista en el JavaScript publicado y solo permite enviar datos de esa aplicación: no lee nada del proyecto ni puede hacerse pasar por otro servicio. El token de escritura de Render no sale nunca al navegador. El nombre del servicio lo pone la aplicación de Logfire, no el código (`configureFrontend` no admite `serviceName` ni `environment`; el entorno va como atributo del recurso).

**Alta, hecha el 13 de noviembre de 2026.** Es configuración de las cuentas; si hay que repetirla (otro proyecto, un token nuevo), los pasos son estos:

1. Logfire → proyecto `oniel` → Frontend → Frontend applications → Create application. El formulario pide el nombre (`oniel-visor`, que no se puede cambiar después y es el nombre del servicio), el entorno (`production`) y un espacio de nombres, que se dejó vacío. La página de la aplicación enseña su token siempre que se quiera («Copy token»).
2. Vercel → proyecto `oniel` → Settings → Environment Variables → `VITE_LOGFIRE_TOKEN` con ese token, tipo Config y solo en Production.
3. Volver a desplegar producción, porque la variable se lee al compilar. Sirve una fusión que toque `frontend/`. El «Redeploy» de un despliegue anterior no sirve si `frontend/` no ha cambiado desde entonces: pasa por el mismo `ignoreCommand` y Vercel lo cancela. Sin una fusión a mano, queda `vercel --prod` («La CLI como respaldo»).
4. Comprobarlo: abrir https://oniel.vercel.app, ejecutar en la consola `setTimeout(() => { throw new Error('prueba de Logfire') })` y, a los diez segundos, buscarlo:

```bash
uv run oniel-data obs consulta "select start_timestamp, service_version, deployment_environment, span_name, exception_message from records where service_name = 'oniel-visor' order by start_timestamp desc limit 5" --horas 1
```

Comprobado así el 13 de noviembre de 2026 con el commit `ade16fe`: el error llegó como `Uncaught error` de `oniel-visor`, nivel 17, con `is_exception`, `deployment_environment = production`, el commit como versión y la ruta `/glosario/via-unica`. Ese primer error no abrió incidencia en «Errores agrupados»: le faltaba la huella por la que Logfire agrupa (`logfire.exception.fingerprint`), que el SDK del navegador no calcula si no se le pide. Desde entonces el visor la envía (`errorFingerprinting: true`). Repetida la prueba con el commit `7f3762e`, dos errores iguales abrieron a los tres minutos una sola incidencia con dos apariciones, de `oniel-visor` y `production`, y llegó su correo («[Logfire Issues] Exceptions»). La incidencia de prueba se puede resolver o borrar en Error tracking.

**Volumen y peso**, medidos el 12 de noviembre de 2026 con el visor compilado y un token de mentira. Una visita sin errores: 0 peticiones a Logfire y 0 registros. Un error: 1 registro; dos errores seguidos salieron en una sola petición de 3,8 kB. El arranque del visor crece 0,9 kB (0,5 kB comprimido). El SDK va en ficheros aparte, 180 kB (55 kB comprimidos), que se piden al arrancar sin esperar a ellos para pintar; los errores que ocurran mientras llegan se guardan (hasta diez) y se envían después. Sin token, lo publicado es idéntico byte a byte a lo de antes.

Un bloqueador de contenido puede cortar las peticiones a Logfire: de esas visitas no llega nada, y el visor funciona igual.

El primer error real llegó ese mismo día: MapLibre lanza `GPUInitializationError` cuando el navegador no tiene WebGL2. Desde #144 el visor lo atiende, explica en el hueco del mapa por qué no hay mapa y no lo envía: es un límite del navegador de quien visita, no un fallo de Oniel.

### Alertas

Una alerta de Logfire es una consulta SQL que se ejecuta cada cierto tiempo sobre una ventana y avisa según el resultado (Alerts → New alert → Custom query). Los canales de aviso se crean una vez en la organización y se eligen en cada alerta: correo a miembros de la organización, Slack, webhook genérico, PagerDuty u Opsgenie. Oniel tiene uno, «Correo», que escribe al correo de la cuenta `ebotiab`; la documentación de Logfire no menciona todavía el canal de correo, pero el formulario lo ofrece. Sin canal, la alerta se evalúa igual y se ve en la página de alertas.

El plan personal no deja comprobar más a menudo que cada 10 minutos, y la ventana no puede pasar de cuatro veces ese intervalo: un fallo tarda hasta 10 minutos en avisar.

Logfire no sondea servicios, y en el plan gratuito de Render la API se suspende sin tráfico: que no lleguen trazas no significa que esté caída, así que no hay alerta de «sin señal». Lo que sí delata un fallo es un arranque que no termina. Las tres alertas están creadas en el proyecto desde el 12 de noviembre de 2026, con el canal «Correo», comprobación cada 10 minutos y aviso en «First match after no matches» (avisa cuando la consulta empieza a dar filas, no en cada comprobación). Sus consultas, probadas antes con `oniel-data obs consulta`, son las de abajo; si se cambian en Logfire, se cambian aquí.

**1. «Oniel: la API no arranca».** Cada arranque del contenedor (tras un despliegue o al despertar) deja primero `import all started` y, cuando la API está lista, `api started`. Avisa si pasan diez minutos sin lo segundo; la importación debería tardar bastante menos (véase «Cargar o refrescar los datos»). Ventana: últimos 30 minutos.

```sql
SELECT service_version AS version,
       max(start_timestamp) FILTER (WHERE span_name = 'import all started') AS arranque,
       max(start_timestamp) FILTER (WHERE span_name = 'api started') AS api_lista
FROM records
WHERE deployment_environment = 'production'
  AND span_name IN ('import all started', 'api started')
GROUP BY service_version
HAVING max(start_timestamp) FILTER (WHERE span_name = 'import all started') < now() - interval '10 minutes'
   AND (max(start_timestamp) FILTER (WHERE span_name = 'api started') IS NULL
        OR max(start_timestamp) FILTER (WHERE span_name = 'api started')
           < max(start_timestamp) FILTER (WHERE span_name = 'import all started'))
```

**2. «Oniel: respuestas 5xx».** Peticiones que terminan en error del servidor o con una excepción no controlada. Ventana: últimos 10 minutos.

```sql
SELECT span_name AS peticion, http_response_status_code AS estado,
       coalesce(exception_type, '') AS excepcion, count(*) AS veces,
       max(start_timestamp) AS ultima, max(trace_id) AS trace_id
FROM records
WHERE deployment_environment = 'production' AND service_name = 'oniel-api'
  AND http_route IS NOT NULL AND parent_span_id IS NULL
  AND (http_response_status_code >= 500 OR level >= 17)
GROUP BY 1, 2, 3
ORDER BY veces DESC
```

**3. «Oniel: importación fallida o sin terminar».** Un tramo `import all` con excepción, o un `import all started` de hace más de diez minutos sin su tramo. Ventana: últimos 30 minutos.

```sql
SELECT 'fallida' AS problema, start_timestamp AS inicio, service_version AS version,
       coalesce(exception_type, '') || ': ' || left(coalesce(exception_message, message), 200) AS detalle,
       trace_id
FROM records
WHERE deployment_environment = 'production' AND service_name = 'oniel-data'
  AND span_name = 'import all' AND (is_exception OR level >= 17)
UNION ALL
SELECT 'sin terminar' AS problema, s.start_timestamp AS inicio, s.service_version AS version,
       'empezó hace más de 10 minutos y no ha dejado su tramo' AS detalle, s.trace_id
FROM records s
LEFT JOIN records f
  ON f.span_name = 'import all' AND f.service_name = 'oniel-data'
 AND f.service_version = s.service_version AND f.start_timestamp >= s.start_timestamp
WHERE s.deployment_environment = 'production' AND s.service_name = 'oniel-data'
  AND s.span_name = 'import all started'
  AND s.start_timestamp < now() - interval '10 minutes'
  AND f.span_id IS NULL
```

La primera y la tercera se disparan a la vez cuando una importación se cuelga; la primera cubre además una API que no levanta con los datos ya cargados. Las alertas y el canal son configuración de la cuenta: los cambia quien la administra, en la web de Logfire.

### Qué dicen las trazas de un despliegue

- **Versión.** En Render la versión del servicio (`service_version`) es el commit desplegado, que Render da en `RENDER_GIT_COMMIT`; en local es la del paquete (`0.1.0`). Las trazas anteriores al 12 de noviembre de 2026 llevan todas `0.1.0`. `/healthz` devuelve también el commit.
- **Arranque.** La API deja una traza `api started` cada vez que arranca: tras un despliegue y cada vez que Render la despierta.
- **Importación.** Cada `oniel-data import all` es un tramo `import all` del que cuelgan los de cada línea, las anotaciones, cada fichero de horarios y la exportación, con `outcome` (`completed`, `skipped` cuando `--if-changed` no encuentra cambios, o `failed` con su excepción), la huella y los recuentos (líneas, ficheros de horarios, viajes). Como un tramo solo se envía al terminar, al empezar deja además un aviso `import all started`: uno sin tramo posterior es una importación en curso o interrumpida. La exportación de la instantánea es un tramo `export snapshot`, que en producción no aparece: el arranque usa `--no-snapshot` y el tramo `import all` lleva `snapshot_exported = false`.

### Consultar el estado: `oniel-data obs`

Desde `backend/`, solo lectura:

```bash
uv run oniel-data obs estado                              # qué corre en producción y cómo va
uv run oniel-data obs estado --verificar --commit <hash> --esperar 15 # verifica la entrega (hasta 15 min)
uv run oniel-data obs estado --verificar --commit <hash> --json       # resultado para automatizaciones
uv run oniel-data obs consulta "select span_name, count(*) n from records group by 1 order by 2 desc" --horas 6
uv run oniel-data obs consulta "select count(*) n from records" --entorno local   # o --entorno todos
```

`obs estado` dice la versión desplegada y desde cuándo, la última importación y su resultado, los errores (nivel 17 o más) y las excepciones controladas desde que entró esa versión, las respuestas 4xx y 5xx por ruta y las rutas más lentas. Como `/healthz` no se traza, la «última traza» de la API es la última petición de un visitante o el último arranque, no la última comprobación de Render. «Última importación» es la de la versión desplegada (con `--commit`, la de ese commit), no la que empezó más tarde: durante un despliegue el contenedor de la versión anterior puede arrancar después que el nuevo y saltarse su importación, y esa omitida no dice nada de la versión nueva (#120). Si la más reciente es de otra versión, la orden la enseña aparte, debajo. Con `--commit` termina con código 1 si ese commit no es el de la API o su importación no ha terminado completada u omitida, y `--esperar` repite la consulta cada 30 segundos hasta que el commit sea el de la API y su importación haya terminado, o hasta que esa importación falle: sustituye a sondear producción con `curl`. El aviso `import all started` y el tramo `import all` van en trazas distintas; una importación en curso es un aviso sin tramo de la misma versión que empiece justo después. `--desde` cambia el inicio del periodo, `--json` da la salida para un programa. `obs consulta` ejecuta SQL sobre la tabla `records` (trazas) o `metrics` y lo imprime en CSV. Las dos órdenes miran `production` salvo que `--entorno` diga `local`; `obs consulta` admite además `--entorno todos`, que no filtra. Usan la API de consultas de Logfire (`POST /v2/query`), que limita las consultas con token de lectura. El token es del proyecto y lo comparten las sesiones que consultan a la vez, así que tras un despliegue es fácil llegar al límite: si Logfire responde 429, la orden lo dice y termina con código 2, salvo con `--esperar`, que espera lo que pide la cabecera `Retry-After` y vuelve a probar dentro del mismo plazo. Las columnas útiles de `records` son `service_name`, `service_version`, `deployment_environment` (`production`, `local`), `span_name`, `message`, `http_route`, `http_response_status_code`, `duration` (segundos), `level`, `is_exception`, `exception_type`, `exception_message`, `attributes`, `trace_id` y `start_timestamp`.

**Verificar una entrega.** Tras fusionar un cambio del backend, usa `obs estado --verificar --commit <SHA de la fusión> --esperar 15`. Es un modo aditivo: sin `--verificar`, el informe y el significado informativo de `--commit` se conservan; que ese informe termine con 0 no certifica ausencia de errores.

El modo estricto requiere un SHA hexadecimal de 7 a 40 caracteres (mejor completo). Solo da éxito si la versión observada más reciente de `oniel-api` coincide, hay una importación de ese mismo SHA terminada con `outcome` explícito `completed` o `skipped`, y no hay errores de servidor de esa versión. Un prefijo que corresponda a varios SHA es evidencia ambigua. Una importación en curso, ausente o sin resultado explícito no certifica nada; si falló, se informa del fallo aunque la API aún no haya arrancado.

El alcance es **la evidencia disponible en Logfire** de `oniel-api` y `oniel-data`, en el entorno indicado (`production` por defecto), durante los últimos `--dias` (7 por defecto). Cada lectura fija un límite superior común; al esperar se conserva el inicio de la ventana. El recuento de errores se filtra por SHA exacto antes de agregarse, sin límite de filas: ni los errores de versiones anteriores ni los de otro entorno o servicio se atribuyen al nuevo commit. Cuenta los registros de nivel 17 o superior y las respuestas HTTP 5xx aunque su nivel sea menor; una excepción controlada de nivel inferior o un 4xx por sí solos no cuentan. Incluye también los errores de la importación anteriores al arranque de la API. `--desde` no se admite en este modo, para evitar recortar esos errores; `--dias` determina el periodo completo. Si el arranque o la importación quedan fuera del periodo, amplía `--dias`.

| Código | `outcome` en JSON | Significado |
|---|---|---|
| 0 | `success` | Commit e importación acreditados y cero errores de servidor observados en la ventana. |
| 1 | `failure` | Fallo observado: error de servidor atribuible al SHA o importación fallida. |
| 2 | `unverifiable` | Verificación imposible: falta token o evidencia, consulta rechazada o sin conexión, respuesta inutilizable, argumentos inválidos o espera agotada. |

`--json` emite un objeto también en los resultados 1 y 2, con `outcome`, `exit_code`, `reason` (identificador del motivo), `message`, `commit`, `environment`, `window_start`, `checked_at` y la evidencia disponible (`api`, `last_import`, `server_errors`, `error_trace_id`). Un recuento `null` significa que no se pudo comprobar; no equivale a cero. Los errores de sintaxis de opciones que detecta el analizador de la CLI conservan su ayuda habitual y código 2.

Sin `--esperar` se hace una lectura con un plazo total de 60 segundos. Con `--esperar N`, las consultas y las pausas comparten el plazo de N minutos: se reintenta cada 30 segundos mientras falte evidencia y, ante 429, se respeta `Retry-After` más un segundo de margen si cabe en el plazo. Al agotarse devuelve 2; no reutiliza un éxito de otra lectura. Un fallo observado termina la espera con 1. El éxito describe lo observado hasta `checked_at`: no garantiza que no aparezcan errores después, ni que Logfire ya haya recibido todas las trazas, y no sustituye las pruebas funcionales del visor.

Una sesión de Claude tiene que ejecutarlo fuera del sandbox del shell, que corta la conexión TLS con Logfire. Cada traza del informe lleva su `trace_id`; se abre en https://logfire-us.pydantic.dev/ebotiab/oniel buscando `trace_id = '…'`.

### El token de lectura

`oniel-data obs` usa un token de **solo lectura** del proyecto, distinto del de escritura de Render. No está en el repositorio ni debe estarlo: se lee de la variable `LOGFIRE_READ_TOKEN` o, si no existe, del fichero `~/.config/oniel/logfire-read-token` (permisos 600) de la máquina de quien desarrolla. Sin token, las órdenes informativas lo dicen y terminan sin fallar; `obs estado --verificar` devuelve 2 (`unverifiable`), también en JSON; el CI no lo tiene ni lo necesita, porque las pruebas simulan las respuestas.

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
