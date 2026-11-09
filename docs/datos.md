# Datos de Oniel: procedencia, licencias y modelo

## Fuentes de esta versión

| Id | Qué aporta | Editor | Licencia | Fecha de consulta |
|---|---|---|---|---|
| `renfe-gtfs-av-ld-md` | Horarios de alta velocidad, larga distancia y media distancia de Renfe (GTFS) | Renfe Viajeros, data.renfe.com | CC BY 4.0 | 2026-11-08 |
| `osm-relation-1254828` | Geometría de la LAV Madrid–Sevilla (vías con `ref=010`, operador Adif) | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `osm-relation-18368327` | Geometría de la línea 300 Madrid–Valencia; Oniel usa Madrid-Atocha–Alcázar de San Juan | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `osm-relation-11351144` | Geometría de la línea 400 Alcázar de San Juan–Cádiz; Oniel usa Alcázar–Córdoba | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `wikipedia-lineas-300-400` | PK de Adif, longitudes y tramos de vía única de las líneas 300 y 400 (verificación) | Colaboradores de Wikipedia | CC BY-SA 4.0 | 2026-11-08 |
| `adif-mapa-red` | Verificación del trazado, códigos de estación y puntos kilométricos de la línea 010 | Adif / Adif Alta Velocidad | Consulta pública | 2026-11-08 |
| `adif-obras-autopista-ferroviaria` | Corte de la línea convencional al sur de Venta de Cárdenas por obras (información de Adif en prensa) | Adif; Europa Press / Demócrata | Consulta pública | 2026-11-08 |
| `openfreemap` | Mapa base del visor | OpenFreeMap · OpenMapTiles · OSM | ODbL / BSD | 2026-11-08 |

El registro completo, con URL, cobertura y notas, está en `backend/data/curated/sources.json` y se sirve en `GET /api/sources`. Los ficheros crudos están en `backend/data/raw/` con fecha en el nombre; su SHA-256 se guarda en la tabla `sources` al importar.

## Líneas cargadas

| Línea | Id | Longitud medida | Nodos | Tramos | Viajes del GTFS |
|---|---|---|---|---|---|
| Alta velocidad Madrid – Sevilla (Adif 010) | `lav-madrid-sevilla` | 470,5 km | 12 | 11 | 335 (AVE, AVLO, Alvia, Intercity) |
| Convencional Madrid – Alcázar de San Juan – Córdoba (Adif 300 y 400) | `convencional-madrid-alcazar-cordoba` | 440,7 km | 26 (2 compartidos) | 25 (11 de vía única) | 503 (MD, Regional Exprés, Proximidad, Alvia, Intercity) |

Madrid-Puerta de Atocha y Córdoba son nodos comunes a las dos líneas: la red forma un lazo Madrid–Córdoba con dos recorridos, el de alta velocidad (343,6 km) y el convencional (440,7 km). Son 814 viajes distintos: 24 Intercity y Alvia Madrid-Atocha Cercanías – Andalucía recorren las dos líneas (la convencional hasta Manzanares y la alta velocidad desde Ciudad Real) y cuentan en ambas.

## Cómo se verificó la LAV Madrid–Sevilla con Adif

El 8 de noviembre de 2026 el servicio WFS/WMS de IDEAdif (`https://ideadif.adif.es/gservices/Tramificacion/wfs`) respondía HTTP 503 y la web de Adif bloquea las descargas automáticas, así que la geometría se tomó de OpenStreetMap y se contrastó con Adif de tres formas:

1. **Longitud**: 470,5 km encadenados entre Atocha y Santa Justa frente a 471,8 km de la línea 010 (diferencia de 1,3 km, coherente con el final de línea más allá del andén).
2. **Puntos kilométricos**: cada nodo se proyecta sobre la geometría y se compara con el PK de referencia de Adif (Ciudad Real 170,7, Puertollano 209,4, Villanueva 285,2, Córdoba 343,7, Bifurcación Málaga 358,0, Santa Justa 470,5). Todas las diferencias quedan por debajo de 1 km; `oniel-data validate` falla si alguna supera 1,5 km.
3. **Códigos de estación**: las paradas del GTFS de Renfe usan los códigos de Adif (60000, 37200, 37300, 37704, 50500, 51003), que coinciden con los nodos.

El mapa oficial de Adif (capa "vía doble electrificada en ancho estándar") se usó como comprobación visual. Cuando IDEAdif vuelva a estar disponible, su GeoJSON puede sustituir a la geometría OSM sin cambiar el modelo: basta con apuntar `geometry_source` a otro fichero.

## Cómo se construyó la línea convencional Madrid–Alcázar–Córdoba

La antigua línea de Andalucía no es una sola línea para Adif: de Madrid a Alcázar de San Juan es parte de la línea 300 (Madrid–Valencia) y de Alcázar a Córdoba, de la 400 (Alcázar–Cádiz). En OpenStreetMap son dos relaciones (`18368327` y `11351144`) que incluyen las dos vías de cada línea doble, ramales y miembros sin orden, así que encadenar sus miembros no da una polilínea. La especificación `convencional-madrid-alcazar-cordoba.json` declara dos `parts`, cada una con su relación y dos puntos (Atocha–Alcázar y Alcázar–Córdoba), y el importador traza el **camino más corto por el grafo de vías** de cada relación y empalma las partes (empalme de 31 m en Alcázar). Cada tramo recuerda de qué relación procede (`segments.source_id`).

Verificación:

1. **Longitud**: 440,7 km medidos frente al PK 442,0 de Córdoba en la numeración de Adif.
2. **Puntos kilométricos**: los PK de Adif recogidos en Wikipedia (Aranjuez 48,7; Alcázar 148,1; Manzanares 197,3; Santa Cruz de Mudela 239,0; Linares-Baeza 314,7; Espeluy 340,9; Andújar 362,8; Córdoba 442,0) quedan entre 0,5 y 1,6 km por encima del kilometraje medido. El desfase es sistemático: Adif conserva la numeración histórica desde Madrid-Atocha y las variantes de trazado posteriores (Aranjuez–Castillejo, Despeñaperros) acortaron la línea sin renumerarla. Por eso esta línea declara `pk_tolerance_km: 2.0`; el PK de Adif se guarda como referencia en cada nodo y el visor muestra el kilómetro medido.
3. **Códigos de estación**: las paradas del GTFS (60200 Aranjuez, 60400 Alcázar, 50100 Manzanares, 50300 Linares-Baeza, 50400 Espelúy, 50403 Andújar…) coinciden con los nodos, situados con las coordenadas de las estaciones de Adif en OSM (`raw/osm/adif_facility_nodes_mancha_andalucia_2026-11-08.json`).
4. **Número de vías**: las etiquetas de OSM no lo cubren en este tramo. Los tramos de vía única se declaran en `track_sections` a partir de Wikipedia y del rutómetro de la línea 400 de la FCMAF: Santa Cruz de Mudela–Vadollano (paso de Despeñaperros, 67 km) y Linares-Baeza–Córdoba (127 km, parte del tramo de vía única que llega hasta Lora del Río). El resto, incluida toda la línea 300, es de vía doble. Vadollano, antigua estación hoy sin servicio, se añadió como punto de referencia para que el límite de la vía única caiga en un nodo.

Límites y avisos:

- **Corte por obras.** Según Adif, entre Venta de Cárdenas y Algeciras no hay circulación desde comienzos de septiembre de 2026 por la adaptación del gálibo de 13 túneles (entre Venta de Cárdenas y Los Cansinos) y otras estructuras para la autopista ferroviaria Algeciras–Madrid–Zaragoza; la reanudación está prevista para otoño de 2027 y es una previsión, no un compromiso. Los horarios GTFS cargados son los planificados y no reflejan este corte: muestran trenes Madrid–Jaén por Despeñaperros y algunos trayectos parciales (Linares-Baeza–Vilches, Linares-Baeza–Mengíbar) que probablemente corresponden a transbordos. El nodo de Venta de Cárdenas lleva esta nota.
- **Servicios incluidos.** El GTFS de Renfe trae AVE, AVLO, Avant, Alvia, Intercity, Euromed, MD, Regional Exprés, Regional y Proximidad, pero no Cercanías: los trenes de la línea C-3 Madrid–Aranjuez no aparecen, y tampoco los de otros operadores ni mercancías.
- **Selección de viajes.** Un viaje se asigna a la línea convencional si para en al menos dos de sus nodos y en alguna de las estaciones que no comparte con la alta velocidad (`min_node_stops` y `any_of_stop_ids` del filtro de corredor). Así entran los MD Madrid–Jaén, Madrid–Alcázar–Albacete, Alcázar–Ciudad Real–Badajoz, Córdoba–Jaén y Cádiz–Jaén, el Alvia Barcelona–Córdoba por Alcázar y los trenes de Proximidad de Córdoba. Los Intercity y Alvia Madrid-Atocha Cercanías–Córdoba–Sevilla/Málaga/Algeciras del fichero (24 viajes, válidos del 8 al 15 de noviembre de 2026) no pasan ese filtro, porque solo paran en Madrid, Ciudad Real y Córdoba, y entran por una regla de recorrido (véase el apartado siguiente).
- **Trenes que cambian de línea.** Esos 24 viajes son los horarios publicados por Renfe tras la interrupción de la alta velocidad en Urda: tardan 2 h 50 entre Madrid y Ciudad Real, compatible solo con ir por la red convencional (Aranjuez, Alcázar de San Juan, Manzanares y la línea Manzanares–Ciudad Real, no cargada), y 1 h 15 entre Ciudad Real y Córdoba, solo posible por la alta velocidad. Cada especificación los declara en `route_overrides`: una regla encaja con los viajes que llevan ciertas paradas seguidas (`consecutive_stop_ids`, en ese orden o en el inverso) y dice entre qué paradas el viaje va por esa línea (`from_stop_id`, `to_stop_id`) y qué asignaciones de parada cambian solo para ellos. La convencional los resuelve entre Madrid y Ciudad Real, saliendo por Manzanares; la LAV, desde Ciudad Real. Los 4 Alvia que no paran en Ciudad Real (Madrid–Córdoba en las mismas 3 h 45) se tratan igual: para ellos Córdoba es salida por Manzanares en la convencional y Madrid-Atocha Cercanías es entrada por Ciudad Real en la LAV. Una asignación con `via` (línea y nodo de enlace) indica que la parada está en otra línea cargada: el reparto de tiempos usa entonces la distancia por esa línea en vez de la línea recta, y el visor explica por dónde sigue el tren. Así estos trenes aparecen en los tramos Madrid–Manzanares de la convencional y Ciudad Real–Córdoba de la alta velocidad, y en ningún otro; `oniel-data validate` avisa si una regla deja de encajar con algún viaje del GTFS.
- **Estaciones compartidas.** Madrid-Puerta de Atocha agrupa en un solo nodo la estación de alta velocidad (60000) y Madrid-Atocha Cercanías (18000), de donde salen los trenes convencionales: forman el mismo complejo. La tabla `stop_mappings` asigna 18000 al nodo, de modo que esos trenes aparecen en «Trenes que paran aquí».

## Modelo de datos

Pensado para añadir líneas, operadores y medios de transporte sin rehacer la aplicación.

- `sources`: procedencia, licencia, fecha, cobertura y checksum.
- `operators`: operadores y administradores de infraestructura.
- `lines`: una línea por fila, con `mode` (`ferrocarril` hoy; mañana `metro`, `autobús`…), administrador, ancho, electrificación, orden de presentación (`sort_order`) y geometría completa.
- `nodes` + `line_nodes`: los nodos son independientes de la línea; `line_nodes` da su kilómetro y orden en cada línea, así un nodo puede pertenecer a varias líneas (Madrid-Puerta de Atocha y Córdoba lo hacen). `rank` distingue los nodos principales de los secundarios, que el visor atenúa y oculta en el esquema compacto.
- `segments`: tramos entre nodos consecutivos con geometría, velocidad máxima y habitual, número de vías (`tracks`) y la fuente de su geometría.
- `connections`: hacia dónde continúa la red donde Oniel todavía no tiene datos (se dibujan a trazos).
- `stop_mappings`: cómo se resuelve cada parada de un horario contra la red. La tabla es común a todas las líneas; una parada asignada a un nodo por una línea no la degrada otra que la declare como salida. Las reglas de recorrido (`route_overrides` de cada especificación) no se guardan en la base: solo actúan al importar.
- `services`, `service_dates`, `service_stops`: horarios por tren y día, con el operador y la fuente. Cada viaje del GTFS se guarda una sola vez aunque recorra varias líneas.
- `service_segment_passes`: el paso de cada tren por cada tramo, precalculado con las reglas de simulación, línea a línea. Un tren que cambia de línea tiene pasos en cada una solo entre las paradas que le corresponden.
- `import_runs`: historial de importaciones con estadísticas.

## Añadir otra línea

1. Descargar la geometría cruda a `backend/data/raw/` con fecha en el nombre y registrar la fuente en `sources.json`. Si la relación OSM trae las dos vías o miembros desordenados, usar `geometry_source.parts` (relación + punto inicial y final de cada parte); si es una relación limpia, basta `file` + `relation_id`.
2. Escribir `backend/data/curated/<línea>.json` con la línea (`sort_order` para el orden en el visor, `tracks` por defecto; `description` en párrafos separados por una línea en blanco, el primero breve porque el visor lo muestra de entrada y pliega el resto, sin repetir longitud, velocidad, ancho ni electrificación, que ya salen en la ficha), sus nodos (coordenadas o kilómetro; `rank: "secundario"` para los menores; `shared: true` para una estación que ya define otra línea), `track_sections` donde cambie el número de vías, las conexiones y la asignación de paradas. En `corridor_filter`, `min_node_stops` y `any_of_stop_ids` evitan que entren trenes de líneas paralelas. Si un tren recorre esta línea solo en parte y sigue por otra cargada, declararlo en `route_overrides` (paradas seguidas que lo identifican, tramo de paradas que va por esta línea y, si hace falta, la salida con `via` hacia la otra línea).
3. Añadir el id de la línea a `line_ids` en `backend/src/oniel/settings.py` (la primera línea de la lista define los nodos compartidos).
4. `uv run oniel-data validate --spec data/curated/<línea>.json` hasta que no haya problemas.
5. `uv run oniel-data import network` e `import gtfs` (sin `--spec` cargan todas las líneas; `import all` hace todo y exporta la instantánea).

El visor dibuja todo lo que devuelve `GET /api/network`: una pestaña por línea en el panel y todas las líneas en el mapa.
