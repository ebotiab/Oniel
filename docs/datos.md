# Datos de Oniel: procedencia, licencias y modelo

## Fuentes de esta versión

| Id | Qué aporta | Editor | Licencia | Fecha de consulta |
|---|---|---|---|---|
| `renfe-gtfs-av-ld-md` | Horarios de AVE, AVLO, Alvia e Intercity (GTFS) | Renfe Viajeros, data.renfe.com | CC BY 4.0 | 2026-11-08 |
| `osm-relation-1254828` | Geometría de la LAV Madrid–Sevilla (vías con `ref=010`, operador Adif) | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `adif-mapa-red` | Verificación del trazado, códigos de estación y puntos kilométricos | Adif / Adif Alta Velocidad | Consulta pública | 2026-11-08 |
| `openfreemap` | Mapa base del visor | OpenFreeMap · OpenMapTiles · OSM | ODbL / BSD | 2026-11-08 |

El registro completo, con URL, cobertura y notas, está en `backend/data/curated/sources.json` y se sirve en `GET /api/sources`. Los ficheros crudos están en `backend/data/raw/` con fecha en el nombre; su SHA-256 se guarda en la tabla `sources` al importar.

## Cómo se verificó el trazado con Adif

El 8 de noviembre de 2026 el servicio WFS/WMS de IDEAdif (`https://ideadif.adif.es/gservices/Tramificacion/wfs`) respondía HTTP 503 y la web de Adif bloquea las descargas automáticas, así que la geometría se tomó de OpenStreetMap y se contrastó con Adif de tres formas:

1. **Longitud**: 470,5 km encadenados entre Atocha y Santa Justa frente a 471,8 km de la línea 010 (diferencia de 1,3 km, coherente con el final de línea más allá del andén).
2. **Puntos kilométricos**: cada nodo se proyecta sobre la geometría y se compara con el PK de referencia de Adif (Ciudad Real 170,7, Puertollano 209,4, Villanueva 285,2, Córdoba 343,7, Bifurcación Málaga 358,0, Santa Justa 470,5). Todas las diferencias quedan por debajo de 1 km; `oniel-data validate` falla si alguna supera 1,5 km.
3. **Códigos de estación**: las paradas del GTFS de Renfe usan los códigos de Adif (60000, 37200, 37300, 37704, 50500, 51003), que coinciden con los nodos.

El mapa oficial de Adif (capa "vía doble electrificada en ancho estándar") se usó como comprobación visual. Cuando IDEAdif vuelva a estar disponible, su GeoJSON puede sustituir a la geometría OSM sin cambiar el modelo: basta con apuntar `geometry_source` a otro fichero.

## Modelo de datos

Pensado para añadir líneas, operadores y medios de transporte sin rehacer la aplicación.

- `sources`: procedencia, licencia, fecha, cobertura y checksum.
- `operators`: operadores y administradores de infraestructura.
- `lines`: una línea por fila, con `mode` (`ferrocarril` hoy; mañana `metro`, `autobús`…), administrador, ancho, electrificación y geometría completa.
- `nodes` + `line_nodes`: los nodos son independientes de la línea; `line_nodes` da su kilómetro y orden en cada línea, así un nodo puede pertenecer a varias líneas.
- `segments`: tramos entre nodos consecutivos con geometría, velocidad máxima y habitual.
- `connections`: hacia dónde continúa la red donde Oniel todavía no tiene datos (se dibujan a trazos).
- `stop_mappings`: cómo se resuelve cada parada de un horario contra la red.
- `services`, `service_dates`, `service_stops`: horarios por tren y día, con el operador y la fuente.
- `service_segment_passes`: el paso de cada tren por cada tramo, precalculado con las reglas de simulación.
- `import_runs`: historial de importaciones con estadísticas.

## Añadir otra línea

1. Descargar la geometría cruda a `backend/data/raw/` y registrar la fuente en `sources.json`.
2. Escribir `backend/data/curated/<línea>.json` con la línea, sus nodos (coordenadas o kilómetro), conexiones y asignación de paradas.
3. `uv run oniel-data validate --spec data/curated/<línea>.json` hasta que no haya problemas.
4. `uv run oniel-data import network --spec …` y `uv run oniel-data import gtfs --spec …`.

El visor dibuja todo lo que devuelve `GET /api/network`, así que no hace falta tocarlo.
