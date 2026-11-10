# Hoja de ruta de Oniel

Lista ordenada de las tareas pendientes para que Oniel sea útil a más gente. Última revisión: 10 de noviembre de 2026.

## Cómo se usa

- Cada tarea se hace en una sesión aislada, en su rama y en una PR pequeña contra `main`, siguiendo `CLAUDE.md`. El usuario decide qué tarea abre cada sesión; lo normal es la primera de la lista que nadie tenga empezada.
- Cada tarea dice **por qué** se hace, **qué datos** usa, **qué toca** en el código y **cuándo está hecha**. Las condiciones de «hecha» son el criterio de aceptación de la PR.
- Si al hacer una tarea aparece otra, se añade aquí en lugar de hacerse de paso. Al fusionar una tarea, la misma PR la retira de esta lista y añade una línea a «Hecho hasta ahora»; lo aprendido va a `docs/datos.md`, `docs/simulacion.md` o `docs/despliegue.md`.
- Las decisiones de diseño siguen `docs/diseno.md`. Si una tarea necesita una representación nueva (un trazo, un color, un panel), se propone al usuario y, decidida, se anota allí antes de implementarla.
- Toda fuente nueva se registra en `backend/data/curated/sources.json` y su fichero crudo va a `backend/data/raw/` con la fecha en el nombre. Sin fuente, el dato no entra.
- Todo lo que roce los accidentes de Adamuz (18 de enero de 2026) y Urda (28 de octubre de 2026) va en tono sobrio y neutro: hechos, fechas y fuente.

## Hecho hasta ahora

Desde el 8 de noviembre de 2026 se ha fusionado una PR por tarea:

- PR 1: segunda línea, la convencional Madrid – Alcázar de San Juan – Córdoba, con el trazado por el camino más corto en el grafo de vías de OSM, los tramos de vía única y los MD, Regional Exprés y Proximidad del GTFS.
- PR 2: trenes que cambian de línea, con reglas de recorrido (`route_overrides`) para los 24 Intercity y Alvia Madrid-Atocha Cercanías – Andalucía que, tras Urda, van por la convencional hasta Manzanares y por la alta velocidad desde Ciudad Real.
- PR 3: esquema de línea sin rótulos solapados.
- PR 4: carga del visor desde la instantánea estática, con sondeo de la API en segundo plano y despertar de Render sin reimportar.
- PR 5, 6 y 7: documentación del despliegue vigente en Vercel (la clase de PR que la tarea 10 hace innecesaria).
- PR 8: panel de línea con cabecera más ligera, descripción por párrafos y una sola nota.
- PR 9: mapa acotado a la península y sus vecinos, siempre con el norte arriba.
- PR 10 y 11: CI en GitHub Actions, `CLAUDE.md` y esta hoja de ruta.
- PR 12: tercera línea, la convencional Manzanares – Ciudad Real (Adif 522, vía única), y los 24 Intercity y Alvia desviados recorriendo las tres líneas tramo a tramo, sin distancias en línea recta. Era la tarea 1 de esta lista.

## Orden

2. Capa de interrupciones vigentes, con fuente y fecha
3. Trenes diarios por tramo y por operador, con Iryo y Ouigo
4. Capa de proyectos e infraestructura planeada
5. Glosario didáctico de los términos del mapa
6. Sistema de señalización por tramo
7. Comparador de recorridos entre dos estaciones
8. Cobertura por estación: destinos directos y frecuencias
9. Refresco automático del GTFS
10. Conectar Vercel a GitHub

Las tareas 2 a 4 amplían los datos; 5 y 6 explican lo que ya se ve; 7 y 8 son herramientas nuevas sobre los datos existentes; 9 y 10 son infraestructura. El orden es orientativo: 5, 9 y 10 no dependen de nada y pueden adelantarse si conviene. Cada tarea conserva su número aunque se retiren las anteriores, para que las referencias entre tareas y entre sesiones sigan valiendo.

## Tareas

### 2. Capa de interrupciones vigentes, con fuente y fecha

**Por qué.** Los horarios GTFS son los planificados y no reflejan dos interrupciones que Oniel conoce solo como texto: el corte de la convencional entre Venta de Cárdenas y Algeciras por obras de gálibo (sin circulación desde comienzos de septiembre de 2026, reanudación prevista para otoño de 2027, según Adif) y la interrupción de la alta velocidad Madrid – Andalucía tras el accidente de Urda (desde el 28 de octubre de 2026). Hoy están en una nota del nodo Venta de Cárdenas, en `sources.json` y en `docs/`. El visitante debería ver en el mapa y en el panel qué tramos no tienen circulación, desde cuándo, hasta cuándo se prevé y según quién, y la simulación debería saber que una alternativa que pase por un tramo cortado no está disponible.

**Qué datos usa.** La fuente `adif-obras-autopista-ferroviaria` ya está registrada. Para la alta velocidad hace falta una fuente nueva con fecha de consulta: comunicados de Adif y de Renfe o información del Ministerio de Transportes sobre el estado de la circulación en cada tramo (qué tramos reabrieron, con qué condiciones, qué sigue cortado). Cada interrupción registra: tramos afectados (ids de `segments`), fecha de inicio, fecha prevista de fin o ninguna, naturaleza (obras; interrupción tras un accidente), fuente, fecha de la última comprobación y una frase en tono neutro. Si la situación cambia, se actualiza con la fecha; no se infiere nada.

**Qué toca.** Un fichero curado `backend/data/curated/interrupciones.json` con su modelo en `oniel.network.spec` (y validación: los ids de tramo existen, las fechas son coherentes), una migración `0004` con la tabla `disruptions`, la carga en `oniel.network.importer`, un endpoint `GET /api/disruptions` (o un campo en `/api/network`) y su exportación en la instantánea (`network.json` o un fichero propio). En el visor: `frontend/src/map/layers.ts` (trazo distinto para los tramos cortados; la representación se decide con el usuario y se anota en `docs/diseno.md`, porque el rojo hoy significa «cierre simulado»), `SegmentDetail.tsx` y `StripDiagram.tsx` (aviso con fechas y fuente), `Legend.tsx` y `CoveragePanel.tsx` (fecha de la última comprobación). En la simulación, `network_repo.fetch_alternatives` o su presentación indica cuándo la alternativa cruza un tramo cortado. Pruebas: carga y validación del fichero, API, y una prueba Playwright del panel de un tramo cortado (modo estático). Documentación: sección «Interrupciones» en `docs/datos.md`; el punto 4 de lo que no hace la simulación en `docs/simulacion.md`.

**Hecha cuando.** Las dos interrupciones se ven en el mapa y en el panel con fecha de inicio, previsión de fin, fuente y fecha de comprobación; la simulación de un cierre en la LAV avisa si la alternativa por Despeñaperros está cortada; `validate` falla si un id de tramo no existe; la nota del nodo Venta de Cárdenas se apoya en el mismo dato; `sources.json` registra la fuente de cada interrupción; instantánea regenerada.

### 3. Trenes diarios por tramo y por operador, con Iryo y Ouigo

**Por qué.** Las barras del esquema («trenes el 13 nov») y las listas de trenes cuentan solo a Renfe. Por el tronco Madrid – Córdoba circulan también Iryo y Ouigo (Madrid – Sevilla y Madrid – Málaga), así que la carga real del tronco está infravalorada, justo donde más interesa medirla. Separar las cuentas por operador permite decir cuántos trenes al día pasan por cada tramo y de quién son, sin interpretar nada más.

**Qué datos usa.** Los GTFS de Iryo y de Ouigo España. Primero comprobar si los publican en el Punto de Acceso Nacional de transporte multimodal del Ministerio de Transportes (nap.transportes.gob.es) o en sus propias webs, con qué licencia y con qué validez; registrar cada uno en `sources.json` y guardarlo en `backend/data/raw/<operador>/` con la fecha. Si un operador no publica GTFS, se documenta la ausencia y no se reconstruyen horarios por otros medios. Las paradas de esos ficheros pueden no usar los códigos de Adif: hace falta una asignación de sus `stop_id` a los nodos, como ya hace `stop_mappings`. El día de referencia de la instantánea debe caer dentro de la validez de todos los ficheros.

**Qué toca.** `import gtfs` ya admite `--feed`, `--source-id` y `--operator-id`; `import all` usa un único fichero (`FEED_DEFAULT` en `oniel/cli/main.py`): generalizarlo a una lista de alimentaciones (fichero, fuente, operador), por ejemplo en `settings.py` o declarada en `sources.json`. Los operadores se insertan desde `operators` de cada especificación (`oniel.network.importer`): añadir Iryo y Ouigo. El exportador (`oniel.export.snapshot`) y `GET /api/segment-counts` desglosan por operador; `GET /api/segments/{id}/services` y `/api/nodes/{id}/services` ya devuelven el operador de cada servicio o lo añaden. En el visor, `StripDiagram.tsx` muestra el desglose (cómo, se decide con el usuario: barras apiladas, cifra al pasar, lista en el panel), `SegmentDetail.tsx` agrupa «Trenes que lo recorren» por operador y `CoveragePanel.tsx` enumera los operadores con su fuente. Pruebas: `test_corridor_filter.py` y `test_integration_db.py` con los recuentos nuevos, prueba del desglose en la API, Playwright del panel de un tramo de la LAV. Documentación: tabla de fuentes, «Servicios incluidos» y tabla de líneas en `docs/datos.md`; «Limitaciones conocidas» en `docs/simulacion.md`.

**Hecha cuando.** Cada tramo de la LAV muestra los trenes del día de referencia por operador (Renfe, Iryo, Ouigo) y la convencional indica que solo tiene Renfe; las fuentes están registradas con licencia y validez; `validate` y las pruebas pasan con los recuentos nuevos; instantánea regenerada.

### 4. Capa de proyectos e infraestructura planeada

**Por qué.** Entender cómo está conectada la red incluye lo que está previsto, en obras o parado. Alrededor de las líneas cargadas hay al menos cuatro casos con interés público: la LAV Madrid – Jaén y, en particular, su tramo Mora – Alcázar de San Juan, planeado en 2008–2010 y sin ejecutar; el baipás de Montoro anunciado en 2025; la Variante de Loja y la duplicación de vía de la línea Antequera – Granada. Mostrarlos con su estado, su fecha y su fuente, sin valorarlos, ayuda a situar la red actual.

**Qué datos usa.** Fuentes oficiales: notas de prensa y estudios informativos del Ministerio de Transportes, licitaciones y notas de Adif, anuncios del BOE (aprobación de estudios informativos, declaraciones de impacto ambiental) y la Declaración sobre la Red. Cada proyecto registra: nombre, qué une, estado (en estudio, en proyecto, licitado, en obras, parado, sin ejecutar), fechas conocidas con su fuente, geometría (un esbozo como los `sketch` de `connections`, o el trazado si la fuente lo da), a qué línea o nodo se asocia si procede, y la fecha de la última comprobación. Las fechas y los estados de los cuatro casos citados se comprueban en las fuentes antes de escribirlos; esta lista solo los nombra. La Variante de Loja y la duplicación Antequera – Granada quedan fuera de las líneas cargadas: la capa debe admitir geometrías que no cuelgan de ningún nodo.

**Qué toca.** Fichero curado `backend/data/curated/proyectos.json` con su modelo y validación en `oniel.network.spec`, migración con la tabla `projects`, carga en el importador, `GET /api/projects` y exportación en la instantánea. En el visor: una capa a trazos en `layers.ts` distinta de las conexiones no cargadas (representación decidida con el usuario y anotada en `docs/diseno.md`; el color solo si significa estado), entrada en `Legend.tsx`, lista en `CoveragePanel.tsx` o un panel propio, y una ficha al seleccionar un proyecto (estado, fechas, fuente). Pruebas: carga y validación, API, Playwright de la ficha. Documentación: sección «Proyectos» en `docs/datos.md`.

**Hecha cuando.** Los cuatro proyectos se ven en el mapa con su estado y, al seleccionarlos, su ficha con fechas, fuente y fecha de comprobación; cada uno tiene su entrada en `sources.json`; `validate` comprueba el fichero; instantánea regenerada.

### 5. Glosario didáctico de los términos del mapa

**Por qué.** Un principio de `docs/diseno.md` es que los textos hablan al visitante que sabe poco de ferrocarril. El visor ya usa términos que no todo el mundo conoce: tramo, vía única y doble, PAET, puesto de banalización, bifurcación, cambiador de ancho, punto kilométrico, ancho ibérico y estándar, electrificación, velocidad máxima y habitual, paso publicado, estimado e indeterminado, horario planificado, operador y administrador de infraestructura, bloqueo y señalización (que la tarea 6 añade). Cada uno debería explicarse a un toque de distancia, en el sitio donde aparece.

**Qué datos usa.** Ninguno externo obligatorio: definiciones propias, breves, en español llano y tono neutro. Si se cita el glosario de Adif o la Declaración sobre la Red, se registra como fuente.

**Qué toca.** Un módulo `frontend/src/panel/glosario.ts` con los términos y sus definiciones, un componente de término (botón accesible, no solo al pasar el ratón, que funcione en móvil) usado en `KindBadge.tsx`, `SegmentDetail.tsx`, `NodeDetail.tsx`, `StripDiagram.tsx`, `Legend.tsx` y `SimulationPanel.tsx`, y una sección «Glosario» completa en `CoveragePanel.tsx` o en un panel propio accesible desde la cabecera, con su ruta (`#/glosario`). Prueba Playwright: tocar «PAET» en el nodo de Urda muestra la definición; el glosario completo es accesible. Documentación: una línea en `docs/diseno.md` sobre dónde y cómo se muestran las definiciones, decidida con el usuario.

**Hecha cuando.** Todos los términos técnicos visibles en el panel tienen definición a un toque, el glosario completo se abre desde el visor, los textos están revisados en tono y longitud, y las pruebas estática y de tipos pasan.

### 6. Sistema de señalización por tramo

**Por qué.** El sistema de protección del tren y el bloqueo de cada tramo (ASFA, LZB, ERTMS; bloqueo automático, control de tráfico centralizado) determinan cómo se separan los trenes y a qué velocidad pueden circular. Es parte de cómo está conectada la red y aparece en la conversación pública sobre los dos accidentes de 2026; Oniel debe mostrar el dato por tramo, con fuente y fecha, sin interpretación.

**Qué datos usa.** La Declaración sobre la Red vigente de Adif y de Adif Alta Velocidad, cuyos anexos recogen por línea y tramo el sistema de señalización, el de protección del tren y el bloqueo. Se descarga a `backend/data/raw/adif/` con la fecha y se registra en `sources.json` (consulta pública, © Adif). Las etiquetas de OpenStreetMap pueden servir de contraste, no de fuente.

**Qué toca.** En cada especificación, un bloque `signalling_sections` análogo a `track_sections` (de nodo a nodo: protección del tren, bloqueo, mando) que `oniel.network.build` reparte a los tramos; una migración que añada esos campos a `segments`; `validate` exige cobertura completa; el modelo de tramo de la API y la instantánea los incluyen; `SegmentDetail.tsx` los muestra en la ficha del tramo con enlace al glosario (tarea 5). Pruebas: construcción de la red con secciones, validación de cobertura, Playwright del panel de un tramo. Documentación: `docs/datos.md` (fuente, correspondencia entre la Declaración y los campos).

**Hecha cuando.** Todos los tramos de las líneas cargadas muestran protección del tren y bloqueo con su fuente; `validate` falla si falta alguno; instantánea regenerada.

### 7. Comparador de recorridos entre dos estaciones

**Por qué.** Con dos lazos (Madrid – Córdoba, y Madrid – Manzanares – Ciudad Real desde que está cargada la tercera línea), la pregunta natural es «¿cómo se va de A a B y qué diferencia hay entre un camino y otro?»: kilómetros, tiempo estimado, kilómetros de vía única, estaciones servidas, trenes directos. Generaliza el recorrido alternativo de la simulación, que hoy solo encuentra una línea entre dos nodos compartidos: `fetch_alternatives` no ve un desvío que encadene dos líneas, como el de Madrid a Ciudad Real por la convencional hasta Manzanares y la línea de Manzanares a Ciudad Real (260,5 km frente a 170,8 km por la alta velocidad), que es justo el que hacen los Intercity y Alvia desviados tras Urda (`docs/simulacion.md`, «Recorrido alternativo»).

**Qué datos usa.** La red cargada (`line_nodes`, `segments` con longitud, `typical_speed_kmh` y `tracks`) y los servicios ya importados (trenes directos y tiempos publicados como referencia real). Las interrupciones de la tarea 2, si existen, para señalar un recorrido cortado. Sin fuentes nuevas.

**Qué toca.** Backend: un módulo de rutas (`oniel.routing` o dentro de `oniel.repo.network_repo`) que construya el grafo de nodos y tramos de todas las líneas y enumere los caminos simples distintos entre dos nodos, con kilómetros, tiempo estimado (longitud entre velocidad habitual, con el método escrito en `docs/simulacion.md`), kilómetros de vía única, estaciones principales y líneas usadas; `GET /api/routes?from=&to=`; la simulación pasa a usarlo para `alternatives`. Para el modo estático, el visor puede calcularlo en el cliente a partir de `network.json`, que ya tiene el grafo. Frontend: panel «Comparar recorridos» con dos selectores de estación, resultados lado a lado y ruta `#/recorridos/<a>/<b>`; el mapa resalta los recorridos (cómo distinguirlos se decide con el usuario según `docs/diseno.md`). Pruebas: unitarias del grafo (Madrid – Córdoba devuelve los dos recorridos), API, Playwright en modo estático. Documentación: sección en `docs/simulacion.md`.

**Hecha cuando.** Madrid – Córdoba muestra los dos recorridos (343,6 km por la alta velocidad; 440,7 km y 194 km de vía única por la convencional) con sus estaciones y trenes directos; Madrid – Ciudad Real muestra también el que pasa por Manzanares, que usa dos líneas, y un cierre entre Madrid y Ciudad Real en la alta velocidad lo señala como alternativa; funciona sin API; la simulación usa el mismo cálculo para la alternativa; pruebas y documentación al día.

### 8. Cobertura por estación: destinos directos y frecuencias

**Por qué.** Quien mira una estación quiere saber a dónde puede ir sin cambiar de tren y cuántas veces al día. El panel de nodo lista hoy los trenes que paran; debería resumir destinos directos con su frecuencia diaria, el tipo de servicio y el operador.

**Qué datos usa.** `services`, `service_stops` (ya guarda `stop_name`) y `service_dates`, ya importados. Los destinos fuera de la red cargada (Málaga, Barcelona, Badajoz…) se nombran con el nombre de la parada del GTFS; para situarlos en el mapa harían falta sus coordenadas de `stops.txt`, que hoy no se guardan.

**Qué toca.** Una consulta en `oniel.repo.services_repo` que, para un nodo y un día, agrupe las paradas posteriores de cada tren en destinos con número de trenes, tipos de servicio, operador y primera y última salida; `GET /api/nodes/{id}/destinations?date=` o un campo nuevo en `/api/nodes/{id}`; exportación en `frontend/public/data/nodes/<id>.json`; sección «Destinos directos» en `NodeDetail.tsx` (ordenada por frecuencia, con enlace al nodo cuando el destino está en la red). Pruebas: unitaria con el GTFS real (Ciudad Real tiene destinos directos a Madrid, Sevilla, Córdoba, Puertollano y Alcázar de San Juan, entre otros), API y Playwright. Documentación: `docs/datos.md`.

**Hecha cuando.** Cada estación muestra sus destinos directos del día de referencia con frecuencia, tipo de servicio y operador, también en modo estático; pruebas en verde; instantánea regenerada.

### 9. Refresco automático del GTFS

**Por qué.** Renfe vuelve a publicar su GTFS con frecuencia; el fichero cargado es del 8 de noviembre de 2026 y los horarios posteriores a Urda que contiene valen solo del 8 al 15 de noviembre. Refrescarlo a mano depende de que alguien se acuerde. Un trabajo programado que descargue el fichero, lo compare y, si cambió, deje una PR con los datos y la instantánea regenerados mantiene Oniel al día y deja la revisión en manos de una persona.

**Qué datos usa.** La URL del conjunto de datos de Renfe en data.renfe.com (CC BY 4.0) ya registrada en `sources.json`; los de Iryo y Ouigo si la tarea 3 está hecha.

**Qué toca.** Primero el código, porque hoy el fichero está fijado por nombre: `FEED_DEFAULT` en `oniel/cli/main.py` y `FEED` en `backend/tests/conftest.py`, y las pruebas afirman recuentos de ese fichero (335, 503 y 154 viajes por línea, 24 viajes con regla de recorrido, 814 servicios) y un caso comprobado a mano del 13 de noviembre de 2026. Decidir y hacer: el fichero de producción se elige por configuración (`ONIEL_GTFS_FEED` o el más reciente de `raw/renfe/`) mientras las pruebas siguen usando el del 8 de noviembre de 2026 como fixture fijo (en `backend/tests/fixtures/` o en `raw/` por nombre), y el día de referencia de la instantánea (`coverage.reference_date`) sigue una regla reproducible dentro de la validez del fichero. La prueba Playwright de la simulación usa la fecha fija del caso a mano y solo corre con la API; con un fichero nuevo necesitará su propia base de pruebas o una fecha derivada. Después el flujo `.github/workflows/gtfs.yml`: `schedule` semanal más `workflow_dispatch`; permisos `contents: write` y `pull-requests: write`; servicio PostgreSQL; pasos: descargar, calcular el SHA-256 y compararlo con el fichero actual, y si cambió guardar `raw/renfe/google_transit_av_ld_md_<fecha>.zip`, actualizar `sources.json` (`file`, `retrieved_on`, validez en `coverage`), ejecutar `validate`, `import all` (regenera la instantánea) y `pytest`, y abrir una PR en una rama `datos/gtfs-<fecha>` con `gh pr create` resumiendo viajes por línea, validez y cambios en los recuentos por tramo. El CI del repositorio se ejecuta sobre esa PR como sobre cualquier otra. Documentación: «Fuentes» en `docs/datos.md` y una sección en `docs/despliegue.md`.

**Hecha cuando.** Una ejecución manual del flujo abre una PR con el fichero nuevo, `sources.json` y la instantánea, y el CI pasa en ella; sin cambios en el fichero, termina sin abrir nada; las pruebas no dependen del fichero de producción; la documentación explica el refresco.

### 10. Conectar Vercel a GitHub

**Por qué.** El visor se publica a mano con la CLI de Vercel después de cada fusión, y se abre una PR de documentación para anotar qué commit está en producción (PR 5, 6 y 7). Conectar el proyecto `oniel` al repositorio hace que `main` se despliegue solo y que cada PR tenga una vista previa para revisar los cambios visuales, y la documentación deja de llevar la cuenta del commit desplegado.

**Qué datos usa.** Ninguno. Necesita la cuenta de Vercel del usuario, que autoriza la aplicación de GitHub: la sesión prepara y documenta, el usuario conecta.

**Qué toca.** En Vercel: proyecto `oniel` → Settings → Git → conectar `ebotiab/Oniel`, con directorio raíz `frontend` y rama de producción `main` (también vale `vercel git connect` desde `frontend/`). Comprobar que `frontend/vercel.json` basta (framework, orden de compilación, carpeta de salida y cabeceras de caché ya están) y que `VITE_API_URL` sigue en los entornos Production y Preview; el backend ya acepta los dominios de vista previa `*.vercel.app` por expresión regular. Opcional: un «Ignored Build Step» que se salte el despliegue cuando el commit no toca `frontend/`. Documentación: reescribir «Visor en Vercel» en `docs/despliegue.md` (el despliegue automático como camino principal, la CLI como respaldo, fuera el párrafo del commit vigente), ajustar la línea de despliegue en `CLAUDE.md` y en la tarea 9 de esta lista. Nada de código.

**Hecha cuando.** Una fusión en `main` publica https://oniel.vercel.app sin la CLI; una PR muestra la comprobación de Vercel con su URL de vista previa; `docs/despliegue.md` y `CLAUDE.md` están al día; no hacen falta más PR de «Docs: el visor sirve tal commit».

## Proteger `main` exigiendo el CI

Es una decisión del usuario; no está activado. El repositorio es público, así que la protección de ramas está disponible en el plan gratuito. Las comprobaciones se llaman como los trabajos de `.github/workflows/ci.yml`: `Backend` y `Frontend`. Tienen que haberse ejecutado al menos una vez para aparecer en la lista de la web; la API acepta los nombres directamente.

Desde la web: Settings → Branches → Add branch protection rule → nombre `main` → «Require status checks to pass before merging» → añadir `Backend` y `Frontend` → Create. O con un conjunto de reglas: Settings → Rules → Rulesets → New branch ruleset → objetivo `main` → «Require status checks to pass» con las dos comprobaciones → Active.

Con `gh api` (protección clásica):

```bash
gh api -X PUT repos/ebotiab/Oniel/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": { "strict": false, "checks": [{ "context": "Backend" }, { "context": "Frontend" }] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

Qué significa cada opción:

- `strict: false` permite fusionar una PR cuyo CI está en verde aunque `main` haya avanzado desde que se creó. Con `true`, cada PR tendría que actualizarse (y volver a pasar el CI) antes de fusionarse; con varias sesiones en paralelo eso añade una vuelta por PR. Se puede empezar en `false`.
- `required_pull_request_reviews: null` no exige PR: un push directo a `main` seguiría siendo posible. Para exigir PR sin exigir aprobaciones (una persona sola con sesiones aisladas), sustituirlo por `{ "required_approving_review_count": 0 }`.
- `enforce_admins: false` deja al administrador saltarse la regla en caso de urgencia; `true` la aplica también a él.

Para ver el estado o retirarla: `gh api repos/ebotiab/Oniel/branches/main/protection` y `gh api -X DELETE repos/ebotiab/Oniel/branches/main/protection`.
