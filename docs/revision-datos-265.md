# Revisión de las fichas (#265)

Revisión del 25 de noviembre de 2026, desde `main` (`407cb1a`, incorporados después `989fe14` y `647a6ab`). La instantánea final se regenera tras incorporar ese último cambio del visor. Son 44 especificaciones: 38 líneas, dos baipases y cuatro enlaces. Las cifras de la incidencia procedían de 41 especificaciones; se han vuelto a contar. Los originales de `data/raw/` no se modifican.

## Reproducción y cadena de procedencia

El visitante arranca con `frontend/public/data/index.json`; al abrir una ficha recibe `lines/<id>.json`. `LineOverview` lee `line.max_speed_kmh` y `line.length_km`; `SegmentDetail`, el máximo y los atributos de su tramo. Esos valores salen del exportador, de las tablas importadas por `network/importer.py` y de `cut_segments` en `network/build.py`. Las secciones curadas prevalecen sobre las etiquetas crudas de la geometría. Las fuentes están registradas en `backend/data/curated/sources.json`.

| Caso | Antes en la instantánea | Corrección y respaldo |
|---|---|---|
| Madrid–Zaragoza–Barcelona, Guadalajara-Yebes–Las Inviernas | Cabecera 300; tramo 310; predominante 300 km/h | Cabecera y tramo 300; predominante 300. OSM: vía **96167462**, `maxspeed=310`, en `raw/osm/relation_11082425_lav_madrid_barcelona_frontera_2026-11-12.json`. Sección curada de 300 según **Adif, mapa 3, página 7** del PDF registrado: máximo de la línea en enero de 2026. No se interpreta como velocidad comercial ni se borra el original discrepante. |
| Burgos–Miranda–Vitoria, Burgos–Briviesca | Cabecera 160; tramo 200; predominante 155 km/h | Cabecera y tramo 160; predominante 155. OSM: vías con `maxspeed=200` como **43909238/43909239**, en `raw/osm/relation_18347132_linea_100_madrid_hendaya_2026-11-17.json`. `wikipedia-linea-100` distingue los 200 de diseño de la variante; **Adif, mapa 3, página 7** da 160 entre Burgos y Miranda. La nueva sección cita esa fuente y la fecha de contraste. |
| Madrid–Sevilla | 470,520 km en cabecera; 470,269 entre nodos extremos | 470,269 km en ambos cálculos (470,3 en la ficha). La geometría de `osm-relation-1254828` sigue unos 251 m después del nodo de Sevilla. No se cambia la referencia independiente de 471,8 km. |
| Venta de Baños–Burgos | 86,735 km en cabecera; 86,272 entre nodos extremos | 86,272 km (86,3 en ficha). La geometría de `osm-relation-4777557` sobrepasa el nodo de Burgos unos 463 m. La referencia de 86,463 km permanece independiente. |
| Electrificación | Texto visible y claves `3kv_cc` / `25kv_ca` mezcladas | Un solo texto en datos de línea y tramo: `Sin electrificar`, `3 kV CC`, `25 kV 50 Hz`; se conservan fuente, ámbito y fecha de cada sección. No cambia la tensión documentada ni la fila que ve el visitante. |
| Vías | Valor heredado sin fuente ni fecha en parte de la red | Secciones explícitas que cubren los huecos de procedencia: mapas 3/4 de Adif para las vías principales, extractos OSM registrados para los enlaces; se conservan las secciones más precisas existentes. Todas las fichas citan ahora la fuente y la fecha. |

El PDF contrastado es `raw/adif/dr-adif-av-2026-mapas_2026-11-12.pdf`, conservado con su fecha de descarga; sus mapas están fechados en enero de 2026. Fuente: [Declaración sobre la Red de Adif](https://www.adifaltavelocidad.es/sobre-adif-av/declaracion-red), identificador `adif-declaracion-red-2026-mapas`. La revisión del fichero existente fue el 25 de noviembre; no se presenta como una nueva descarga ni como una comprobación del estado de circulación de ese día.

**Máxima, predominante y comercial.** El máximo es el mayor de los límites documentados dentro del tramo. La predominante es la etiqueta de velocidad que ocupa más longitud con dato en OSM; puede ser 155 con un máximo de 160. Ninguna es la velocidad comercial de un tren, que incluye su recorrido y sus paradas. Una sección de máxima corrige el límite sin convertir automáticamente la predominante en esa máxima. Si no hay velocidades, se conserva `null`; no se usa cero ni una velocidad de proyecto.

## Convencionales de 155 frente a 160

No eran dos redondeos de una misma magnitud. Se mantienen los 155 cuando los respaldan las fuentes y los tramos cargados:

- **Madrid–Plasencia:** OSM y `wikipedia-linea-500` dan 155; la sección Oropesa–Navalmoral descarta expresamente los 300 de proyecto de la plataforma en obras. El mapa 3 también rotula 155 en el corredor desde Humanes.
- **Monfragüe–Cáceres:** máximo 155 en Monfragüe–Mirabel y 120 predominante; el mapa 3 distingue 155 en ese primer trecho de los 120 de la línea antigua al sur. No son 160 redondeados.
- **Palencia–Santander:** máximo detallado de 155 de OSM, concordante con `wikipedia-linea-palencia-santander`; el mapa 3 resume 160 en Palencia–Alar y Bárcena–Santander. Se conserva la lectura detallada registrada: un rótulo de un corredor no permite asignar 160 a cada uno de sus tramos pequeños. Se deja explícita esta diferencia de escala y fuente; no se declara que los 155 sean de Adif ni que todos los servicios vayan a 155.
- **Sevilla–Huelva:** los 155 de Sevilla–Los Naranjos son una sección ya contrastada con el mapa 3 de Adif; los siguientes tramos tienen 140 y la entrada en Huelva 90. El máximo de la cabecera es 155 por ese primer tramo de la línea 400, no por la línea 440 entera.

Las demás convencionales conservan su máximo calculado de los tramos y sus fuentes. `validate` comprueba las 44 cada vez: ninguna cabecera puede sustituir el máximo por una cifra típica.

Al separar máxima y predominante, los dos tramos Los Naranjos–Cartuja y Cartuja–Benacazón conservan **140 km/h de máxima de Adif** y recuperan **120 km/h predominantes de OSM** (antes se copiaba también 140 en ese campo). Es el único cambio de velocidad predominante de la instantánea: el comparador de Sevilla a Huelva pasa de 51 a 53 minutos orientativos sin paradas, con los mismos 117,0 km. No cambia ningún horario ni recuento de trenes.

## Resolución del número de vías

El número es el de vías principales del recorrido representado, no el de andenes, apartaderos o todas las vías paralelas cercanas. Se han cotejado los símbolos del mapa 3 con las excepciones ya descritas por línea en `docs/datos.md`; las secciones de cambios más precisas conservan sus fuentes originales. Los enlaces, que el mapa no separa, citan los extractos de OSM y sus etiquetas/trazado registrados. Dos límites ya documentados permanecen: los 660 m de vía única a la salida de Burgos no tienen nodo propio y el tramo hasta Briviesca representa la doble vía; la transición próxima a La Vega de la línea de Burgos queda aproximada al nodo de Soto de Cerrato. No se ha cambiado esa resolución ni se presenta el dato como un inventario de cada metro de vía.

## Nombres, descripciones y ausencias

El usuario aprobó el 25 de noviembre el texto de Madrid–Sevilla antes de incorporarlo y el criterio Valencia/Castellón/Alicante en la narración, con nombres ferroviarios íntegros en las estaciones. `Alicante/Alacant-Terminal` está verificado en `stops.txt`, parada **60911**, del GTFS de Renfe registrado. No cambian los identificadores. Las demás descripciones conservan su contenido: solo se normalizan esas grafías. La descripción de Sevilla cita la comprobación del aviso del 13 de noviembre; no afirma haber comprobado de nuevo la interrupción.

Un guion en la tabla siguiente significa ausencia conservada: no hay una fuente verificada para la apertura o la longitud oficial **del recorrido concreto cargado**. Una fuente puede tener una fecha de una línea mayor, una variante o un tramo, sin que se pueda trasladar al recorrido de Oniel. Las referencias existentes no se sustituyen por longitudes de OSM.

Se han revisado **430 tramos**; **332** heredaban vías sin fuente propia y ahora la incluyen. Permanecen **21** fechas de apertura y **24** longitudes de referencia ausentes.

Las citas del visor agrupan solo los atributos con la misma fuente y fecha. Una comprobación nueva de las vías no presenta como recién comprobados otros atributos de esa fuente; la regresión de Pajares conserva por separado las fechas del 15 y el 25 de noviembre.

| Especificación | Máxima km/h | Longitud cargada km | Apertura | Referencia km | Fuentes de vías |
|---|---:|---:|---|---:|---|
| `lav-madrid-sevilla` | 300 | 470.269 | 1992-04-21 | 471.8 | `adif-declaracion-red-2026-mapas` |
| `convencional-madrid-alcazar-cordoba` | 160 | 440.654 | — | 442.0 | `adif-declaracion-red-2026-mapas`, `wikipedia-lineas-300-400` |
| `manzanares-ciudad-real` | 140 | 64.425 | 1861-03-14 | 64.5 | `wikipedia-linea-522` |
| `espeluy-jaen` | 160 | 33.202 | 1881-07-06 | 32.8 | `wikipedia-linea-402` |
| `linares-baeza-moreda-granada` | 140 | 173.673 | 1904-05-02 | 174.2 | `wikipedia-lineas-410-416` |
| `alcazar-albacete` | 200 | 130.747 | 1855-03-18 | 130.6 | `adif-declaracion-red-2026-mapas` |
| `lav-cordoba-malaga` | 300 | 154.687 | 2006-12-16 | 154.517 | `adif-declaracion-red-2026-mapas` |
| `lav-antequera-granada` | 300 | 114.101 | 2019-06-26 | 114.249 | `adif-declaracion-red-2026-mapas`, `boe-b-2025-42383`, `osm-relation-16228313` |
| `lav-madrid-barcelona` | 300 | 626.956 | 2003-10-11 | — | `adif-declaracion-red-2026-mapas` |
| `lav-madrid-valencia` | 300 | 397.398 | 2010-12-18 | 397.55 | `adif-declaracion-red-2026-mapas` |
| `baipas-zaragoza` | 300 | 20.671 | — | — | `adif-declaracion-red-2026-mapas` |
| `baipas-lleida` | 300 | 14.282 | — | — | `adif-declaracion-red-2026-mapas` |
| `lav-albacete-alicante` | 300 | 237.683 | 2010-12-18 | 237.8 | `adif-declaracion-red-2026-mapas` |
| `lav-monforte-murcia` | 200 | 67.724 | 2021-02-01 | 68.442 | `adif-declaracion-red-2026-mapas`, `wikipedia-lav-madrid-levante` |
| `valencia-castello-tarragona` | 220 | 266.455 | 1868-06-21 | — | `adif-declaracion-red-2026-mapas` |
| `enlace-monforte-del-cid` | 100 | 2.137 | 2021-02-01 | — | `osm-relation-18342974` |
| `lav-madrid-valladolid` | 300 | 178.561 | 2007-12-23 | 178.559 | `adif-declaracion-red-2026-mapas` |
| `lav-olmedo-ourense` | 300 | 328.219 | 2021-12-21 | 328.649 | `adif-declaracion-red-2026-mapas`, `osm-relation-11109438`, `osm-relation-4777980`, `wikipedia-lav-olmedo-zamora-galicia` |
| `lav-ourense-santiago` | 300 | 87.841 | 2011-12-10 | 88.28 | `adif-declaracion-red-2026-mapas`, `wikipedia-lav-ourense-santiago` |
| `eje-atlantico` | 200 | 155.201 | 2015-03-29 | 155.6 | `adif-declaracion-red-2026-mapas` |
| `madrid-plasencia` | 155 | 259.800 | — | — | `adif-declaracion-red-2026-mapas`, `wikipedia-linea-500` |
| `lav-plasencia-badajoz` | 200 | 190.896 | 2022-07-19 | — | `adif-declaracion-red-2026-mapas` |
| `ramal-merida` | 120 | 7.456 | — | — | `adif-declaracion-red-2026-mapas` |
| `monfrague-caceres` | 155 | 71.006 | — | — | `adif-declaracion-red-2026-mapas` |
| `lav-valladolid-leon` | 300 | 165.996 | 2015-09-30 | 166.141 | `adif-declaracion-red-2026-mapas`, `wikipedia-lav-valladolid-leon` |
| `lav-venta-de-banos-burgos` | 300 | 86.272 | 2022-07-22 | 86.463 | `adif-declaracion-red-2026-mapas`, `wikipedia-lav-venta-de-banos-burgos-vitoria` |
| `leon-oviedo-gijon` | 200 | 132.522 | — | — | `adif-declaracion-red-2026-mapas` |
| `burgos-miranda-vitoria` | 160 | 117.304 | — | — | `adif-declaracion-red-2026-mapas` |
| `sevilla-cadiz` | 200 | 152.478 | — | — | `adif-declaracion-red-2026-mapas` |
| `lav-barcelona-figueres` | 290 | 132.601 | 2013-01-09 | 131.7 | `adif-declaracion-red-2026-mapas` |
| `lav-la-sagra-toledo` | 220 | 22.220 | 2005-11-15 | 20.842 | `adif-declaracion-red-2026-mapas` |
| `lav-zaragoza-huesca` | 200 | 79.255 | 2003-12-23 | 79.4 | `adif-declaracion-red-2026-mapas` |
| `barcelona-girona-portbou` | 160 | 168.283 | — | — | `adif-declaracion-red-2026-mapas` |
| `tarragona-barcelona` | 160 | 95.560 | — | — | `adif-declaracion-red-2026-mapas`, `osm-relation-5913127` |
| `valencia-xativa-alicante` | 200 | 183.112 | — | — | `osm-relation-16947106` |
| `madrid-avila-valladolid` | 160 | 250.173 | — | — | `adif-declaracion-red-2026-mapas` |
| `palencia-santander` | 155 | 216.978 | — | — | `adif-declaracion-red-2026-mapas` |
| `zaragoza-castejon-logrono` | 160 | 165.636 | — | — | `osm-relation-9277501` |
| `castejon-pamplona` | 140 | 87.343 | — | — | `adif-declaracion-red-2026-mapas` |
| `miranda-bilbao` | 140 | 103.963 | — | — | `osm-relation-9277501` |
| `sevilla-huelva` | 155 | 116.976 | — | — | `adif-declaracion-red-2026-mapas`, `wikipedia-linea-sevilla-huelva` |
| `enlace-soto-de-cerrato` | 160 | 5.170 | — | — | `osm-ramal-soto-de-cerrato` |
| `enlace-aljucen-la-garrovilla` | 120 | 7.102 | — | — | `osm-relation-6759731` |
| `enlace-atocha-chamartin` | 60 | 7.574 | — | — | `osm-relation-18369025` |
