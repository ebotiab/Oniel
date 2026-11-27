# El Chaparral – Arroyo de la Herrera, el camino directo hacia Cáceres

Un tren que viene de Madrid puede pasar de Monfragüe a la vía de Cáceres por el enlace de El Chaparral. Otro puede entrar en Plasencia, hacer su parada y cambiar allí de sentido. Oniel ya distingue esos servicios en los horarios. Falta la vía que permita recorrer el enlace en el mapa y contar qué trenes pasan por él. La carga queda para la [incidencia #323](https://github.com/ebotiab/Oniel/issues/323), sin turno de implementación asignado.

## Qué ofrece hoy el comparador

Comprobación del 27 de noviembre de 2026 sobre [`main` en `a73d8f4`](https://github.com/ebotiab/Oniel/tree/a73d8f48c0086fccbf69412b961f0292a6e59edb). La búsqueda de «Chaparral» y «Herrera» en las incidencias y PR, junto con la revisión de los planes publicados y de la hoja de ruta, dejó este enlace pendiente de preparación. Para este, [#264](https://github.com/ebotiab/Oniel/issues/264) y su [PR #283](https://github.com/ebotiab/Oniel/pull/283) resolvieron cómo mostrar el trazo en las dos fichas. Hay una sola declaración, `enlace-el-chaparral-arroyo-de-la-herrera`, en la especificación de Madrid. Lleva `node_id`, `to_node_id`, los dos textos de destino y el estado `no_cargada`. El comparador solo recorre tramos cargados.

| Consulta sin cierres, repetida en ambos sentidos | Recorridos en el orden del visor | Inversión |
| --- | --- | --- |
| Navalmoral de la Mata ↔ Cáceres | 1. «Por Monfragüe», 130,0 km y 59 min, por Mirabel, Casas de Millán y Cañaveral. 2. «Por Plasencia», 146,4 km y 55 min, por El Chaparral, San Esteban, Plasencia, San Esteban y Arroyo. | Solo el segundo invierte en Plasencia. |
| El Chaparral ↔ Arroyo de la Herrera | Un recorrido, «Por Plasencia», 22,4 km y 10 min. Recorre dos veces el tramo San Esteban–Plasencia. | Plasencia en los dos sentidos. |

Son tiempos teóricos sin paradas. La inversión se incorporó en [#281](https://github.com/ebotiab/Oniel/pull/281). Por eso los 334,5 km históricos de Atocha a Cáceres por San Esteban del [apartado de Extremadura](../datos.md#cómo-se-construyeron-las-líneas-de-extremadura) preceden al comportamiento actual. Hoy Atocha → Cáceres da 333,0 km por Cañaveral o 349,4 km entrando en Plasencia.

Para repetir la tabla desde la raíz de ese commit, con Node 24 y la instantánea versionada, se puede ejecutar el mismo cálculo que llama el visor.

```sh
node --input-type=module <<'JS'
import { readFileSync } from 'node:fs'
import { composeNetwork } from './frontend/src/data/network.ts'
import { buildGraph } from './frontend/src/routing/graph.ts'
import { compararRecorridos } from './frontend/src/app/recorridos.ts'
const red = composeNetwork(JSON.parse(readFileSync('frontend/public/data/index.json', 'utf8')), {})
const grafo = buildGraph(red)
for (const [a, b] of [['navalmoral-de-la-mata', 'caceres'], ['bif-el-chaparral', 'arroyo-de-la-herrera']]) {
  for (const [desde, hasta] of [[a, b], [b, a]]) {
    for (const { titulo, route } of compararRecorridos(grafo, red, desde, hasta, new Map()).recorridos) {
      console.log(desde, hasta, titulo, route.length_km, route.time_min, route.node_ids, route.reverse_node_ids)
    }
  }
}
JS
```

## Dónde unir las vías

Adif inventaría **4,8 km de línea 534** entre El Chaparral y Arroyo. El mapa y el pliego del Ministerio sitúan la alternativa por Plasencia. Desde la 530 se toma la 536 hasta San Esteban y la 538 hasta la estación. Al salir se vuelve a San Esteban y se toma la 026 hacia Cáceres. La línea 500 por Cañaveral constituye un tercer itinerario desde Monfragüe. [Declaración sobre la Red 2026][dr] · [Mapas de Adif, pp. 4 y 8][mapas] · [Pliego de la nueva estación de Plasencia, apartado 3, p. 4][pliego].

| Empalme | Identidad que se reutiliza en Oniel (longitud, latitud) | Contraste de Adif y OSM |
| --- | --- | --- |
| Lado de Madrid | `bif-el-chaparral`, en `madrid-plasencia` (−6,1475609, 39,9554043) | El nodo Adif `B3500` reúne 530, 534 y 536. La aguja OSM `8047113244` (−6,1475798, 39,9555029) es vértice común de las vías de Madrid y del enlace. Queda a 11 m de la posición curada y a 50 m del extremo del eje cartográfico de Adif. |
| Lado de Cáceres | `arroyo-de-la-herrera`, en `lav-plasencia-badajoz` (−6,1910900, 39,9464500) | En el nodo Adif `03500` la 534 alcanza la 026. El fin de la etiqueta OSM 534, `5007593878` (−6,1869497, 39,9491046), queda a 37 m del extremo del eje Adif y a **460 m** del punto curado. Desde él hay continuidad por vía hasta la 026. |

Se contrastaron `RailwayLink_055340010` y los tramos adyacentes del GML de Adif (versión `2026/01`, eje de 4,846 km) con las descargas OSM del 13/11/2026. En la relación de servicio 6759731, seleccionar `railway=rail` y `ref=534` da, desde El Chaparral, las vías **570083420 → 863767829 → 863767828 → 754709650**. Comparten vértices consecutivos. Con `trace_osm_relation(raw, None, origen, destino, way_ref="534")` y las dos posiciones de la tabla, `polyline.length_km` mide **4,830209 km a la ida y 4,830209 km a la vuelta** (71 vértices). [GML de Adif][gml] · [Vías del enlace][osm534] · [Vías de Madrid][osm530] · [Vías de la 026][osm026].

**Propuesta de empalme en Arroyo.** Los 460 m superan el máximo de proyección de Oniel (400 m). Acercar las líneas con una recta ocultaría la aguja real. La vía OSM `1046552626`, sin `ref`, une el último vértice de la 534 con `9624185392` (−6,1883402, 39,9482663), vértice exacto del trazado cargado de la 026. Son 0,150797 km adicionales. Trazando en la relación 6759731 entre `8047113244` y `9624185392` se obtienen **4,981005 km en cada sentido**. Se propone conservar los dos ID públicos, situar sus posiciones compartidas en esas agujas y cortar allí las líneas. El corte de Arroyo pasaría del km medido 12,277 al 11,967 de la línea de Plasencia. Declarar por separado los 4,8 km del inventario y la longitud dibujada hasta la unión de vías. Verificar al importar que las geometrías comparten extremo y que cada metro de vía se carga una vez. [Trazador y límite de proyección](../../backend/src/oniel/network/build.py) · [Extracto OSM][osm534].

**Atributos pendientes.** Adif da 1.668 mm y consigna la 534 sin electrificar. OSM etiqueta sus cuatro vías como únicas de ancho ibérico, la primera sin catenaria (2,726 km, 85 km/h) y las otras tres con 25 kV a 50 Hz (2,105 km, 200 km/h). El Ministerio documenta servicios con tracción eléctrica en el corredor Monfragüe–Cáceres desde diciembre de 2023, sin localizar el comienzo de la catenaria en la 534. Antes de declarar la electrificación por secciones y la velocidad del enlace, contrastar sus límites con el inventario vigente y los mapas 3 y 4. Verificar también protección, bloqueo y mando en el ámbito exacto, incluida la vía de aguja. [Declaración de Adif][dr] · [Mapas][mapas] · [Consulta de la nota de Transportes y del dosier de apertura][ministerio].

## Qué tren pasa por cada recorrido

Se comprobó el **viernes 20/11/2026** en las tres ediciones de Renfe AV/LD/MD guardadas en Oniel. Se expandieron `calendar.txt` y `calendar_dates.txt`, se ordenó `stop_times.txt` por `stop_sequence` y se agruparon las variantes del mismo número activas ese día con `oniel.gtfs.reader.read_feed`. En las ediciones del 08/11 y del 12/11 los dos ejemplos figuran como **Alvia**. En la del 17/11, como **Intercity**, con las mismas paradas y horas del ejemplo. [GTFS archivados][horarios] · [Lector de Oniel](../../backend/src/oniel/gtfs/reader.py).

| Tren Madrid-Chamartín → Badajoz | Paradas consecutivas que lo distinguen el 20/11 | Recorrido que debe comprobar la carga |
| --- | --- | --- |
| **00190**, salida 08:30 | Navalmoral `35206` 11:09–11:10, Monfragüe `30000` 11:39–11:40, Cáceres `35400` 12:18–12:20. | Candidato al directo. En Madrid–Plasencia se resuelve hasta El Chaparral y en la 026 desde Arroyo. Hoy ninguna de las dos especificaciones le aplica una regla especial. Falta el tramo intermedio en el que contar su paso estimado. |
| **00194**, salida 18:20 | Navalmoral `35206` 20:55–20:56, **Plasencia `30002` 21:42–21:47**, Cáceres `35400` 22:21–22:23. El GTFS permite subir y bajar en Plasencia. | Entra por El Chaparral y San Esteban, invierte en la estación y vuelve por San Esteban hacia Arroyo. Le corresponden cero pasos por la 534. |

En el ZIP del 17/11 los pares de `trip_id` originales activos son `0019012026-11-17` y `0019022026-11-17` para el directo, y `0019412026-11-17` y `0019422026-11-17` para el que entra. Comparten `route_id=1700037606GL023` y llevan `shape_id` vacío. El pliego oficial describe la incorporación a la LAV y la alternativa convencional. Transportes documenta el uso del corredor Monfragüe–Cáceres por los Alvia y Renfe confirmó la recuperación de la parada ferroviaria en Plasencia el 10/08/2026. Estas fuentes respaldan la interpretación física. Falta una marcha de Adif o Renfe identificada por número y fecha que confirme las agujas del **00190** el 20/11. Una expedición sin parada intermedia también podría ir por Cañaveral o sufrir un desvío. [Pliego][pliego] · [Nota de Transportes][ministerio] · [Aviso de Renfe][aviso].

La relación OSM 6759731 se titula «Alvia 00194 Madrid → Badajoz» y lleva las vías del directo. Asignar el 00194 por ese rótulo borraría una parada comercial publicada para el día estudiado. Usar sus vías como geometría. Para asignar servicios, contrastar por fecha la secuencia de paradas con el itinerario físico y dejar explícita la estimación mientras falte evidencia individual. [OSM archivado][osm534] · [GTFS archivados][horarios].

### Reglas que la carga debe conservar

- En [Madrid–Plasencia](../../backend/data/curated/madrid-plasencia.json), `a-plasencia-desde-navalmoral` y `a-plasencia-desde-monfrague` cortan en `30002` con `to_stop_id`. En [Plasencia–Badajoz](../../backend/data/curated/lav-plasencia-badajoz.json), `desde-plasencia-tras-navalmoral` y `desde-plasencia-tras-monfrague` reanudan allí con `from_stop_id`. Responden a las parejas consecutivas `35206/30002` y `30000/30002` en cualquiera de los dos sentidos. El 00194 activa la primera pareja de reglas. El 17012, con Monfragüe y Plasencia consecutivas, prueba la segunda.
- Para el enlace, seleccionar el patrón acreditado de **Monfragüe y Cáceres consecutivas**, en ambos órdenes. Examinar las variantes y excluir Plasencia, Mirabel `35301`, Casas de Millán `35302` y Cañaveral `35303`. El regional 17018 para en Plasencia y luego en la vía antigua. Respetar las salidas `aside` de esta última en San Esteban y Casa de la Torre. La ausencia de `30002` por sí sola también admitiría servicios ajenos.
- Dar al enlace su propio filtro y asignaciones. En los `via` que ahora saltan de El Chaparral a Arroyo, insertar el enlace como primer paso desde Madrid y en orden inverso desde la 026. Conservar el resto de la cadena hacia Mérida, Badajoz y Madrid y las salidas por San Esteban de los que entran en Plasencia. Los empalmes son puntos de paso sin parada comercial.

## Recuentos para contrastar la importación

| Población de referencia | Valor anterior a la carga |
| --- | --- |
| Edición completa del **08/11**, usada en `test_extremadura.py` | De 172 viajes que pasan de Monfragüe hacia El Chaparral o a la inversa, 96 entran en Plasencia (37 por el patrón de Navalmoral y 59 por el de Monfragüe) y 76 pasan de la convencional a la 026 por el hueco. La pareja consecutiva Monfragüe–Cáceres da 76 viajes normalizados en cada uno de los tres ZIP. |
| **20/11**, edición del **17/11**, día que auditó #264 | 20 servicios en Monfragüe–El Chaparral y 12 en El Chaparral–San Esteban. En la 026 hay 14 en Plasencia–San Esteban, 12 en San Esteban–Arroyo, 20 en Arroyo–El Palmeral y 22 en Casa de la Torre–Cáceres. La vía antigua lleva 2. El enlace a trazos carece de tramo que contar. La cifra de **8** de #264 se reproduce al enumerar los candidatos del GTFS (00190, 00192, 00293, 00295, 37090, 37093, 37095 y 37492). |
| Instantáneas por edición y actual | Las ediciones del 08/11 y 12/11 tienen como día de referencia el **13/11**. Para la del 17/11 es el **20/11**. La instantánea conjunta de `main` usa el **11/12/2026**, el laborable de mayor oferta en la ventana común de los horarios vigentes. En esos tramos da las mismas cifras. Son servicios programados por número y día. |

Comparar conjuntos de identidades además de totales. La igualdad `20 − 12 = 8` permite detectar una pérdida de pasos, pero por sí sola no identifica qué trenes tomaron el enlace. Un número comercial compartido con otro puede corresponder al mismo material. Oniel cuenta por número, operador y día dentro de cada edición. [Recuentos del 20/11][hist20] · [Pruebas del fichero del 08/11][pruebas] · [Instantánea de Madrid][snap-madrid] · [Instantánea de la 026][snap-lav].

## Archivos y pruebas de la futura PR de datos

1. **Especificación y fuentes.** Incorporar `backend/data/curated/enlace-el-chaparral-arroyo-de-la-herrera.json` con `link_of: lav-plasencia-badajoz`, ambos nodos `shared` y la zona Extremadura. Registrar el ID tras sus dos líneas en `backend/src/oniel/settings.py`. En `madrid-plasencia.json`, retirar la conexión a trazos. Ajustar posiciones, textos y `via` allí y en `lav-plasencia-badajoz.json`. Revisar las referencias desde las demás líneas. En `sources.json`, ampliar la cobertura de las fuentes reutilizadas y registrar las nuevas, sus condiciones y la consulta fechada en `backend/data/raw/`.
2. **Continuidad y sentido.** Medir vía a vía entre los dos empalmes en ambos sentidos, validar las uniones y verificar las fichas y el mapa. Probar Monfragüe → El Chaparral → Arroyo → El Palmeral y el inverso sin inversión. Probar también El Chaparral → San Esteban → Plasencia → San Esteban → Arroyo y el inverso. Solo en la estación se cambia de sentido. El recorrido por Cañaveral debe seguir disponible.
3. **Comparador estático y API.** La regla genérica de triángulos de `link_of` puede vetar el paso entre los dos brazos de San Esteban antes de calcular la inversión. En una prueba en memoria sobre el índice de referencia, con una arista entre los empalmes y los lados de las agujas, declarar `link_towards: bif-el-palmeral` en la especificación del enlace conservó el directo y el camino con inversión. Repetir con la geometría ya importada. Para Navalmoral ↔ Cáceres comparar `findRoutes` sobre la instantánea y `GET /api/routes?from=navalmoral-de-la-mata&to=caceres` sobre la misma importación. Con parámetros normales debe aparecer el directo. Repetir con `max_ratio=100` en ambos motores para incluir la entrada en Plasencia, que el límite habitual de 2 puede ocultar por la longitud del rodeo. Exigir igual orden, tramos y nodos en secuencia, kilómetros, minutos y `reverse_node_ids`. Añadir los casos a `backend/tests/test_routing.py`, `frontend/e2e/fixtures/rutas-paridad.json`, `frontend/e2e/rutas.spec.ts` (incluido `@api`) y `frontend/e2e/extremadura.spec.ts`.
4. **Servicios y pasos.** Incluir el enlace en `backend/tests/conftest.py` y ampliar `backend/tests/test_extremadura.py` e integración. Sobre la misma edición y fecha, exigir igualdad antes/después de `(operador, número, fecha)` y de la secuencia de paradas con horas y permisos de subida/bajada. Para el 00190 comprobar un paso estimado por el enlace entre las horas de Monfragüe y Cáceres. Para el 00194 comprobar la parada de Plasencia, los dos brazos correctos y cero pasos por la 534. Repetir con el viaje de vuelta y el control de Cañaveral. En cada edición exigir un único paso por `(dataset_id, service_id, segment_id)`, también en San Esteban–Plasencia aunque la ruta lo recorra al entrar y al salir. Conciliar los ocho números en sus tramos vecinos y explicar cada diferencia por tren, fuente y fecha.
5. **Importación y publicación.** Desde `backend/`, con base propia vacía y el futuro `main` actualizado, ejecutar `uv run oniel-data validate --spec data/curated/enlace-el-chaparral-arroyo-de-la-herrera.json`, `uv run oniel-data validate` y `uv run oniel-data import all`. Exigir resolución completa, cero pasos indeterminados y ausencia del antiguo trazo en las dos fichas. Regenerar `frontend/public/data/` en esa PR, revisar los recuentos históricos, las alternativas, las medidas y las tablas de `docs/datos.md`, `docs/simulacion.md` y `AGENTS.md`. Pasar pytest, los casos estáticos afectados y la integración con API local según la [guía de Oniel](../../AGENTS.md). Solo la PR de implementación podrá cerrar #323.

## Fuentes y condiciones de uso

Consulta de esta preparación, 27/11/2026. La fecha de cada copia permite repetir las medidas aunque cambie el original.

| Editor y material | Edición y condiciones |
| --- | --- |
| Adif y Adif Alta Velocidad, [Declaración sobre la Red][dr] y [mapas archivados][mapas] | Edición de 27/02/2026. Libro, anexos de características y longitudes. Mapas archivados el 12/11, fuente `adif-declaracion-red-2026-mapas`. Consulta pública, © Adif y Adif Alta Velocidad. |
| [IDEAdif, Red de Transporte Ferroviario][ide], [copia del GML][gml] | Versión interna 2026/01, copia del 07/08/2026. Atribución «© Administrador de infraestructuras ferroviarias». El [metadato oficial][meta] declara uso sin condiciones. |
| Colaboradores de OpenStreetMap, [6759731][osm534], [6759679][osm530] y [8117446][osm026] | Extractos de 13/11/2026, ODbL 1.0. IDs `osm-relation-6759731`, `osm-relation-6759679` y `osm-relation-8117446` en el [registro de fuentes](../../backend/data/curated/sources.json). |
| Renfe Viajeros, [GTFS AV/LD/MD][horarios] y [aviso de restablecimiento][aviso] | ZIP del 08, 12 y 17/11/2026, CC BY 4.0. El aviso del 27/07/2026 es una publicación de Renfe de consulta pública. |
| Ministerio de Transportes, [pliego de octubre de 2023][pliego] y [consulta archivada][ministerio] | Documentación oficial de consulta pública. © Ministerio. Se citan los hechos publicados y se remite a los originales. El registro de Oniel documenta las condiciones de las notas consultadas el 13/11/2026. |

[dr]: https://www.adifaltavelocidad.es/documents/34745/51134530/20260227_01%2BDR%2BAdif_AV%2B2026_Libro.pdf/60f60247-935c-6d14-3ac4-8886c5e74dd6?t=1772454129932
[mapas]: ../../backend/data/raw/adif/dr-adif-av-2026-mapas_2026-11-12.pdf
[pliego]: https://contrataciondelestado.es/wps/wcm/connect/b4ea3fb1-0f8b-40d2-892f-4d254f167d47/DOC20231110131202PPTP.pdf?MOD=AJPERES
[ide]: https://datos.gob.es/es/catalogo/e0dat0002-red-de-transporte-ferroviario-de-adif1
[gml]: https://github.com/ArturoVazquez/atlas-archivo/blob/4677145ef514b0030de5adce3b5fce5501a44b2a/fuentes/adif/2026/2026-08-07_adif_red-ferroviaria-wfs-inspire.zip
[meta]: https://www.idee.es/csw-codsi-idee/srv/api/records/62c487b1-6816-4594-a800-218abe896994/formatters/xml
[osm534]: ../../backend/data/raw/osm/relation_6759731_alvia_madrid_badajoz_2026-11-13.json
[osm530]: ../../backend/data/raw/osm/relation_6759679_linea_530_monfrague_plasencia_2026-11-13.json
[osm026]: ../../backend/data/raw/osm/relation_8117446_lav_madrid_extremadura_2026-11-13.json
[horarios]: ../../backend/data/raw/renfe/
[aviso]: https://grupo.renfe.com/es/es/sala-de-prensa/avisos/2026/julio/renfe-restablece-servicio-monfrague-plasencia
[ministerio]: ../../backend/data/raw/proyectos/consultas_2026-11-13_lav_plasencia_badajoz.json
[hist20]: ../../frontend/public/data/historico/renfe-gtfs-av-ld-md-2026-11-17/segment-counts.json
[pruebas]: ../../backend/tests/test_extremadura.py
[snap-madrid]: ../../frontend/public/data/lines/madrid-plasencia.json
[snap-lav]: ../../frontend/public/data/lines/lav-plasencia-badajoz.json
