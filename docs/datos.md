# Datos de Oniel: procedencia, licencias y modelo

## Fuentes de esta versión

| Id | Qué aporta | Editor | Licencia | Fecha de consulta |
|---|---|---|---|---|
| `renfe-gtfs-av-ld-md` | Horarios de alta velocidad, larga distancia y media distancia de Renfe (GTFS) | Renfe Viajeros, data.renfe.com | CC BY 4.0 | 2026-11-08 |
| `ouigo-gtfs-nap` | Horarios de alta velocidad de Ouigo España (GTFS) | OUIGO España, en el Punto de Acceso Nacional del Ministerio de Transportes y Movilidad Sostenible | Licencia de datos abiertos del Ministerio (nap.transportes.gob.es/licencia-datos) | 2026-11-12 |
| `iryo-web` | Que Iryo opera en la LAV Madrid–Sevilla y no publica sus horarios en un formato abierto | Iryo; Punto de Acceso Nacional | Consulta pública; © Iryo | 2026-11-11 |
| `osm-relation-1254828` | Geometría de la LAV Madrid–Sevilla (vías con `ref=010`, operador Adif) | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `osm-relation-18368327` | Geometría de la línea 300 Madrid–Valencia; Oniel usa Madrid-Atocha–Alcázar de San Juan | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `osm-relation-11351144` | Geometría de la línea 400 Alcázar de San Juan–Cádiz; Oniel usa Alcázar–Córdoba | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-08 |
| `wikipedia-lineas-300-400` | PK de Adif, longitudes y tramos de vía única de las líneas 300 y 400 (verificación) | Colaboradores de Wikipedia | CC BY-SA 4.0 | 2026-11-08 |
| `osm-relation-6759901` | Geometría de la línea 522 Manzanares–Ciudad Real (vías de la relación del servicio regional Alcázar de San Juan–Badajoz) | Colaboradores de OpenStreetMap | ODbL 1.0 | 2026-11-10 |
| `wikipedia-linea-522` | Número de línea de Adif, PK, longitud, vía única y fechas de apertura de la línea Manzanares–Ciudad Real (verificación) | Colaboradores de Wikipedia | CC BY-SA 4.0 | 2026-11-10 |
| `fcmaf-linea-522` | Tipo de vía, electrificación, PK, códigos de estación y velocidades de la línea 522 (verificación) | Federación Castellano Manchega de Amigos del Ferrocarril | Consulta pública; © FCMAF | 2026-11-10 |
| `adif-mapa-red` | Verificación del trazado, códigos de estación y puntos kilométricos de la línea 010 | Adif / Adif Alta Velocidad | Consulta pública | 2026-11-08 |
| `adif-obras-autopista-ferroviaria` | Corte de la línea convencional al sur de Venta de Cárdenas por obras (información de Adif en prensa) | Adif; Europa Press / Demócrata | Consulta pública | 2026-11-08 |
| `adif-estado-de-la-red` | Aviso de la interrupción de la alta velocidad Madrid–Andalucía y tramos que siguen en servicio | Adif | Consulta pública | 2026-11-10 |
| `adif-aviso-obras-autopista-ferroviaria` | Aviso de la interrupción por obras entre Córdoba y Santa Cruz de Mudela | Adif | Consulta pública | 2026-11-10 |
| `adif-salidas-y-llegadas` | Paneles de salidas y llegadas de cuatro estaciones: hasta dónde llegan los trenes a cada lado de una interrupción | Adif | Consulta pública | 2026-11-10 |
| `renfe-nota-md-jaen-madrid-2026-09` | Inicio de las obras el 6 de septiembre de 2026 y servicio por carretera entre Jaén y Almuradiel | Renfe | Consulta pública | 2026-11-10 |
| `el-estrecho-digital-corte-algeciras` | Previsión de fin de las obras (otoño de 2027) y límite del corte de la vía en Venta de Cárdenas | El Estrecho Digital | © del medio; se cita el dato | 2026-11-10 |
| `europa-press-reapertura-madrid-sevilla` | Estimación del Ministerio de Transportes sobre la reanudación de la alta velocidad | Europa Press; Pressdigital | © de la agencia; se cita el dato | 2026-11-10 |
| `boe-reglamento-circulacion-ferroviaria` | Referencia de los conceptos de circulación del glosario (bloqueo y cantón, marcha a la vista, puesto de mando, ASFA, LZB y ERTMS) | Agencia Estatal Boletín Oficial del Estado | Texto legal; aviso legal del BOE | 2026-11-12 |
| `openfreemap` | Mapa base del visor | OpenFreeMap · OpenMapTiles · OSM | ODbL / BSD | 2026-11-08 |

El registro completo, con URL, cobertura y notas, está en `backend/data/curated/sources.json` y se sirve en `GET /api/sources`. Los ficheros crudos están en `backend/data/raw/` con fecha en el nombre; su SHA-256 se guarda en la tabla `sources` al importar. Los ficheros de horarios se declaran además en la lista `feeds` del mismo `sources.json`, uno por descarga (véase «Conjuntos de datos»); el de Renfe lo descarga cada semana un flujo de GitHub Actions, que abre una PR cuando el horario publicado ha cambiado (véase «Refresco de los horarios»). Las seis fuentes del 10 de noviembre de 2026 son las de las interrupciones del servicio: avisos, paneles y noticias que cambian, de modo que su fichero crudo es un registro de lo que decían ese día (`raw/interrupciones/consultas_2026-11-10.json`), resumido y sin copiar el texto. Lo mismo vale para la consulta sobre los horarios de Iryo (`raw/operadores/consultas_2026-11-11.json`).

### Operadores y sus horarios

Los operadores de trenes de cada línea se declaran en `operators` de su especificación, cada uno con su fuente. Al importar se guardan en `operators` y `line_operators`, y la API los devuelve en `operators` de la cobertura y en `operator_ids` de cada línea.

| Operador | Líneas | Horarios | Fuente |
|---|---|---|---|
| Renfe Viajeros (`renfe`) | las tres | Cargados | `renfe-gtfs-av-ld-md`, CC BY 4.0 |
| Ouigo España (`ouigo`) | LAV Madrid – Sevilla | Cargados | `ouigo-gtfs-nap`, licencia de datos abiertos del Ministerio de Transportes |
| Iryo (`iryo`) | LAV Madrid – Sevilla | No publicados (`timetable: "no_publicado"`) | `iryo-web` |

- **Ouigo** publica su GTFS en el Punto de Acceso Nacional de Transporte Multimodal (nap.transportes.gob.es, conjunto 1515). La descarga exige una cuenta de usuario, gratuita. La licencia permite reutilizar los datos con fines comerciales o no, citando la fuente con la indicación «Powered by MITRAMS» y un enlace a https://www.transportes.gob.es/, sin alterar los metadatos de actualización y manteniendo al día lo que se muestra; el panel de cobertura la cita con su enlace. El fichero es del 2 de julio de 2026 y vale del 26 de junio al 12 de diciembre de 2026: hay que descargar el siguiente a mano antes de esa fecha, y el flujo de refresco lo recuerda con una incidencia tres semanas antes (véase «Refresco de los horarios»).
- **Iryo** no publica sus horarios en GTFS ni en otro formato reutilizable. El 11 de noviembre de 2026 no figuraba entre los 27 conjuntos ferroviarios del Punto de Acceso Nacional (el buscador no devuelve nada para «iryo» ni para «ILSA»), su web solo ofrece el buscador de billetes y Transitland no lo tiene. Existe un fichero elaborado por un particular, sin licencia declarada, que no se usa. Oniel no reconstruye sus horarios por otros medios: Iryo queda registrado como operador de la LAV sin horarios, sus trenes no están en los recuentos y el visor lo dice en cada tramo de la línea, en la nota del esquema y en la cobertura. Si Iryo publica un GTFS, basta declararlo en `feeds` y quitar `timetable` de su entrada en la especificación.
- **Particularidades del fichero de Ouigo.** Es una conversión de los horarios que el operador comunica a la base europea MERITS de la UIC, y la entrada de `feeds` declara cómo leerlo. Sus `stop_id` son el código UIC, «0071» seguido del código de estación de Adif: `stop_id_prefix` quita el prefijo al leer, así que sus paradas son las mismas que las del fichero de Renfe y valen las asignaciones de `stop_mappings` sin duplicarlas (solo hubo que añadir Zaragoza-Delicias y Barcelona-Sants como salidas por Madrid). Rotula todos los trenes como «TGV» y escribe «TGV 6477» como número: `product` los rotula «Ouigo» y el lector deja el número solo. Los nombres de parada vienen en mayúsculas y sin tildes; el lector los pasa a mayúscula inicial («Madrid-Puerta de Atocha») y el visor abrevia los que conoce.
- `oniel-data validate` comprueba que cada operador con horarios cargados tiene un fichero declarado, que cada fichero es de un operador declarado en alguna línea, que un operador sin horarios publicados no tiene ninguno y que los ficheros vigentes coinciden en algún día (`common_validity`).

## Líneas cargadas

| Línea | Id | Longitud medida | Nodos | Tramos | Viajes del GTFS |
|---|---|---|---|---|---|
| Alta velocidad Madrid – Sevilla (Adif 010) | `lav-madrid-sevilla` | 470,5 km | 12 | 11 | 335 de Renfe (AVE, AVLO, Alvia, Intercity) y 25 de Ouigo |
| Convencional Madrid – Alcázar de San Juan – Córdoba (Adif 300 y 400) | `convencional-madrid-alcazar-cordoba` | 440,7 km | 26 (2 compartidos) | 25 (11 de vía única) | 503 (MD, Regional Exprés, Proximidad, Alvia, Intercity) |
| Convencional Manzanares – Ciudad Real (Adif 522) | `manzanares-ciudad-real` | 64,4 km | 4 (2 compartidos) | 3 (los 3 de vía única) | 154 (MD, Regional Exprés, Intercity, Alvia) |

En «compartidos» se cuentan los nodos que define otra línea. Son 975,6 km de red, 30 estaciones y 839 viajes distintos (814 de Renfe y 25 de Ouigo), porque un viaje que recorre varias líneas cuenta en cada una y se guarda una sola vez:

- Madrid-Puerta de Atocha y Córdoba son comunes a la alta velocidad y a la convencional: la red forma un lazo Madrid–Córdoba con dos recorridos, el de alta velocidad (343,6 km) y el convencional (440,7 km).
- Manzanares (de la convencional) y Ciudad Real (de la alta velocidad) son los extremos de la tercera línea, que cierra un segundo lazo: de Madrid a Ciudad Real hay 170,8 km por la alta velocidad y 260,5 km por la convencional hasta Manzanares (196,1 km) y la línea de Manzanares a Ciudad Real (64,4 km).
- Los 130 MD y Regional Exprés de la línea de Manzanares a Ciudad Real vienen de Alcázar de San Juan o siguen hacia allí, así que ya estaban en la convencional, donde cuentan solo hasta Manzanares.
- 24 Intercity y Alvia Madrid-Atocha Cercanías – Andalucía recorren las tres líneas (la convencional hasta Manzanares, la tercera entera y la alta velocidad desde Ciudad Real) y cuentan en las tres.
- Los 25 viajes de Ouigo son 8 Madrid–Sevilla, 13 Madrid–Málaga y 4 que enlazan Barcelona con Sevilla o Málaga parando en Madrid-Puerta de Atocha; los de Málaga dejan la línea en la bifurcación de Málaga. Ninguno recorre las líneas convencionales.

El día de referencia, el viernes 13 de noviembre de 2026, cada tramo de la LAV lleva los trenes de los dos operadores:

| Tramos de la LAV | Renfe | Ouigo | Total |
|---|---|---|---|
| Madrid-Puerta de Atocha – Urda – Ciudad Real (4 tramos) | 72 | 12 | 84 |
| Ciudad Real – Córdoba – bifurcación de Málaga (5 tramos) | 96 | 12 | 108 |
| Bifurcación de Málaga – Majarabique | 49 | 6 | 55 |
| Majarabique – Sevilla-Santa Justa | 47 | 6 | 53 |

En las dos líneas convencionales todos los trenes son de Renfe. Los de Ouigo solo paran en Madrid, Córdoba y Sevilla o Málaga, así que su paso por cada tramo es siempre estimado. `GET /api/segment-counts` da el total por tramo (`counts`) y su reparto por operador (`by_operator`); el detalle de cada línea, `counts_by_operator`.

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

## Cómo se construyó la línea Manzanares–Ciudad Real

Para Adif es la línea 522, «Manzanares a Ciudad Real»: 64,5 km de vía única electrificada de ancho ibérico, abierta por tramos entre el 1 de octubre de 1860 y el 14 de marzo de 1861. El número de línea se comprobó en Wikipedia, que cita la relación de líneas del Ministerio de Fomento, y en la ficha de la FCMAF; no se dio por supuesto.

OpenStreetMap no tiene una relación de infraestructura propia de esta línea (ninguna `route=railway` ni `route=tracks` pasa por Daimiel). Las vías sí están, dentro de la relación `6759901`, que describe el servicio regional de Renfe «Alcázar de San Juan – Badajoz» y cuyas vías empiezan en Manzanares. La especificación `manzanares-ciudad-real.json` declara una sola parte con esa relación y dos puntos, la estación de Manzanares y la de Ciudad Real, y el importador traza el camino más corto por el grafo de vías, el mismo método que la convencional.

Verificación:

1. **De estación a estación.** El trazado empieza a 44 m del punto de la estación de Manzanares (el nodo de la convencional) y termina a 63 m del de Ciudad Real (el nodo de la alta velocidad). Sube hacia el noroeste hasta Daimiel y baja a Almagro antes de entrar en Ciudad Real: por eso mide 64,4 km y no los 47 km que separan las dos estaciones en línea recta.
2. **Longitud.** 64,4 km medidos frente a 64,5 km (Wikipedia) y a 64,464 km entre los PK de las dos estaciones (FCMAF, que cuenta 64,6 km hasta la topera del final de línea).
3. **Puntos kilométricos.** La línea 522 continúa la numeración desde Madrid: Manzanares es el PK 197,319, Daimiel el 218,799, Almagro el 240,112 y Ciudad Real el 261,783. La especificación lo declara con `pk_origin_km: 197.319`, y `oniel-data validate` compara cada PK con el kilómetro medido más ese origen: las diferencias son de 40 a 60 m.
4. **Códigos de estación.** Las paradas del GTFS (50100 Manzanares, 94002 Daimiel, 94004 Almagro, 37200 Ciudad Real) coinciden con los códigos de Adif de Wikipedia y de la FCMAF. Daimiel y Almagro se sitúan con las coordenadas de las estaciones de Adif en OSM (`raw/osm/adif_facility_nodes_mancha_andalucia_2026-11-08.json`); quedan a 13 m y 5 m del trazado.
5. **Número de vías y velocidad.** Vía única en toda la línea, según Wikipedia y la FCMAF («vía única electrificada», con la electrificación en servicio desde el 28 de noviembre de 1975); las vías de OSM que llevan el dato dicen `passenger_lines=1`. La velocidad máxima de las vías en OSM es 140 km/h, que es la que da la FCMAF para la mayor parte del recorrido. La FCMAF anota la tensión como 3.300 V en continua; Oniel escribe 3 kV CC, el valor nominal que usa en las otras líneas convencionales.

Las vías del recorrido llevan `operator=Adif`, ancho de 1668 mm y 3000 V; solo unas pocas están rotuladas, como «Línea Manzanares-Ciudad Real» (`ref=522`), y la entrada a la estación de Ciudad Real figura como línea 520. Las estaciones cerradas (Azuer, El Campillo, Pozuelo de Calatrava) y Ciudad Real-Miguelturra, donde arranca el ramal a la bifurcación Poblete, no se han cargado como nodos: ningún tren del GTFS para en ellas.

Con la línea cargada desaparece la conexión a trazos que salía de Manzanares, y de Ciudad Real sale ahora, también a trazos, la línea convencional hacia Puertollano, Mérida y Badajoz (Adif 520), que no está cargada. Entre Ciudad Real y Puertollano esa línea corre pegada a la de alta velocidad; el croquis la dibuja algo separada, al oeste, para que se distinga.

## Límites y avisos

- **Corte por obras.** Desde el 6 de septiembre de 2026 no circulan trenes de viajeros entre Almuradiel-Viso del Marqués y Alcolea de Córdoba, por la adaptación del gálibo de 13 túneles (entre Venta de Cárdenas y Los Cansinos) y otras estructuras para la autopista ferroviaria Algeciras–Madrid–Zaragoza. Está registrado en `interrupciones.json` con sus fechas y sus fuentes (véase «Interrupciones del servicio»). Los horarios GTFS cargados son los planificados y no lo reflejan: muestran trenes Madrid–Jaén por Despeñaperros y algunos trayectos parciales (Linares-Baeza–Vilches, Linares-Baeza–Mengíbar) que probablemente corresponden a transbordos. El visor marca esos tramos en rojo y añade una nota a sus listas de trenes; el panel de Venta de Cárdenas y el de cualquier otro nodo del corte muestran la interrupción a partir del mismo dato.
- **Servicios incluidos.** El GTFS de Renfe trae AVE, AVLO, Avant, Alvia, Intercity, Euromed, MD, Regional Exprés, Regional y Proximidad, pero no Cercanías: los trenes de la línea C-3 Madrid–Aranjuez no aparecen. El de Ouigo trae todos sus trenes de alta velocidad. Faltan los de Iryo, que no publica sus horarios (véase «Operadores y sus horarios»), y las mercancías. En la LAV se cuentan los trenes que paran en Córdoba y en alguna estación de Madrid: quedan fuera los que la recorren sin parar en Madrid (los AVE de Renfe entre Barcelona y Andalucía por el baipás) y un Ouigo Madrid–Málaga sin parada en Córdoba que solo circuló del 26 de junio al 14 de julio de 2026.
- **Selección de viajes.** Un viaje se asigna a la línea convencional si para en al menos dos de sus nodos y en alguna de las estaciones que no comparte con la alta velocidad (`min_node_stops` y `any_of_stop_ids` del filtro de corredor). Así entran los MD Madrid–Jaén, Madrid–Alcázar–Albacete, Alcázar–Ciudad Real–Badajoz, Córdoba–Jaén y Cádiz–Jaén, el Alvia Barcelona–Córdoba por Alcázar y los trenes de Proximidad de Córdoba. A la línea de Manzanares a Ciudad Real se asigna el que para en al menos dos de sus cuatro estaciones, porque entre ellas no hay otro recorrido: son 130 viajes, MD y Regional Exprés de Alcázar de San Juan, Madrid, Albacete, Alicante o Valencia a Ciudad Real y Badajoz, y todos paran en las cuatro. Los Intercity y Alvia Madrid-Atocha Cercanías–Córdoba–Sevilla/Málaga/Algeciras del fichero (24 viajes, válidos del 8 al 15 de noviembre de 2026) no pasan ninguno de los dos filtros, porque solo paran en Madrid, Ciudad Real y Córdoba, y entran por una regla de recorrido (véase el apartado siguiente).
- **Trenes que cambian de línea.** Esos 24 viajes son los horarios publicados por Renfe tras la interrupción de la alta velocidad en Urda: tardan 2 h 50 entre Madrid y Ciudad Real, compatible solo con ir por la red convencional (Aranjuez, Alcázar de San Juan, Manzanares y la línea de Manzanares a Ciudad Real), y 1 h 15 entre Ciudad Real y Córdoba, solo posible por la alta velocidad. Cada especificación los declara en `route_overrides`: una regla encaja con los viajes que llevan ciertas paradas seguidas (`consecutive_stop_ids`, en ese orden o en el inverso) y dice entre qué paradas el viaje va por esa línea (`from_stop_id`, `to_stop_id`) y qué asignaciones de parada cambian solo para ellos. La convencional los resuelve entre Madrid y Ciudad Real, saliendo por Manzanares; la de Manzanares a Ciudad Real, entre las mismas paradas, entrando por Manzanares; la LAV, desde Ciudad Real. Los 4 Alvia que no paran en Ciudad Real (Madrid–Córdoba en las mismas 3 h 45) se tratan igual: para ellos Córdoba es salida por Manzanares en la convencional y salida por Ciudad Real en la tercera línea, que cruzan sin parar, y Madrid-Atocha Cercanías es entrada por Ciudad Real en la LAV.
- **Paradas que están en otra línea cargada.** Una asignación con `via` indica que la parada es un nodo de otra línea y por dónde se llega a ella: la línea y el nodo por el que el tren entra. Si el camino cruza más de una línea, `via` es una lista, un trecho por línea (de Manzanares a Córdoba: la línea de Manzanares a Ciudad Real y, desde Ciudad Real, la alta velocidad). El reparto de tiempos usa entonces los kilómetros por esas líneas en vez de la línea recta, y el visor explica por dónde sigue el tren. Las asignaciones generales también lo usan: Daimiel, Almagro y Ciudad Real son, para la convencional, salidas por Manzanares hacia la tercera línea, y Alcázar de San Juan o Madrid son, para la tercera, salidas por Manzanares hacia la convencional. Así los 24 trenes desviados aparecen en los tramos Madrid–Manzanares de la convencional, en los tres de la línea de Manzanares a Ciudad Real y en Ciudad Real–Córdoba de la alta velocidad, y en ningún otro. `oniel-data validate` avisa si una regla deja de encajar con algún viaje del GTFS o si un `via` no se puede seguir (una línea que no está cargada, un nodo de enlace que no es común a las dos líneas, una parada que no es nodo de la última).
- **Estaciones compartidas.** Madrid-Puerta de Atocha agrupa en un solo nodo la estación de alta velocidad (60000) y Madrid-Atocha Cercanías (18000), de donde salen los trenes convencionales: forman el mismo complejo. La tabla `stop_mappings` asigna 18000 al nodo, de modo que esos trenes aparecen en «Trenes que paran aquí». Ciudad Real es una sola estación para la alta velocidad y para la línea de Manzanares: su nodo lo define la LAV y la tercera línea lo incorpora con `shared: true`, igual que hace con Manzanares, que define la convencional.

## Anotaciones de red

Una anotación es algo que pasa sobre la red entre dos fechas según una fuente: hoy, una interrupción del servicio; después, una obra o un proyecto. Todas comparten un modelo (`AnnotationSpec`, en `oniel.network.spec`), un fichero curado, una tabla (`annotations`) y un endpoint (`GET /api/annotations`), de modo que un tipo nuevo no trae su propia fontanería.

**Un solo fichero.** Todas van en `backend/data/curated/anotaciones.json`, en la lista `annotations`, cada una con su `kind`. Se prefirió a un fichero por tipo porque así los ids son únicos sin más comprobación, hay un cargador y una orden de importación, y un tipo nuevo no añade ficheros ni configuración. Cada tipo se sigue revisando a su ritmo: lo que marca la revisión es el `checked_on` de cada entrada, no el fichero.

| Campo | Qué es |
|---|---|
| `id` | Identificador estable y único entre todos los tipos. |
| `kind` | El tipo, uno de los declarados (hoy, `interrupcion`). |
| `status` | El estado, uno de los que admite su tipo. |
| Alcance | Uno de tres, y solo uno: `line_id` con `from_node` y `to_node` (de un nodo a otro de una línea, en el orden del kilometraje, con todos los tramos que quedan entre ambos); `node_id` (un nodo de la red cargada); o `geometry` (una geometría GeoJSON propia, en WGS 84, para lo que no cuelga de la red cargada). |
| `start_date`, `expected_end_date`, `expected_end_text`, `ended_on` | Las fechas, en días completos. La anotación está vigente los días `start_date` ≤ día < `ended_on`, sin límite por el lado que falte. |
| `title`, `reason` | El nombre propio de lo anotado y el motivo o la descripción en una frase neutra. Hace falta al menos uno; cada tipo dice cuál exige. |
| `note` | Precisión opcional. |
| `source_ids` | Ids de `sources.json`. La primera es la fuente principal, y tiene que tener URL. |
| `checked_on` | Día de la última comprobación en las fuentes. |

**Los tipos se declaran en el código**, en `ANNOTATION_KINDS` (`backend/src/oniel/domain/annotations.py`). Cada uno dice sus estados válidos, cuáles de ellos dan la anotación por terminada (llevan `ended_on`, y solo ellos), qué alcances admite, qué campos opcionales exige y si corta la circulación en sus tramos:

| Tipo | Estados | Alcances | Exige | Corta la circulación |
|---|---|---|---|---|
| `interrupcion` | `vigente`, `terminada` (con `ended_on`) | de nodo a nodo | `start_date`, `reason` | Sí |

**Añadir un tipo** son dos entradas, sin migración, endpoint ni capa nuevos:

1. Declararlo en `ANNOTATION_KINDS` con sus estados, sus alcances y los campos que exige. Desde ahí lo validan `oniel-data validate` y la importación, lo guarda la tabla `annotations` (el tipo y el estado son texto: no hay que tocar el esquema) y lo sirven `GET /api/annotations`, el índice y el detalle de cada línea.
2. Darle una entrada en el registro de capas del visor, `frontend/src/app/annotationLayers.ts`: cómo se marcan sus tramos en el mapa y en el esquema, su entrada de leyenda, su ficha, sus notas en las listas y su apartado en «Qué hay en esta versión». El mapa, la leyenda, el esquema y los paneles leen de ese registro. Los colores y los textos de la entrada son una decisión de diseño: se proponen y se anotan en `docs/diseno.md`. Un tipo sin entrada se sirve pero no se enseña.

Lo que no está hecho todavía es el dibujo en el mapa de una anotación con geometría propia: llegará como un campo más de la entrada del registro con el primer tipo que la use (los proyectos, #18). Las anotaciones de un nodo se sirven con el detalle de las líneas a las que pertenece.

`oniel-data validate` comprueba el fichero sin base de datos y termina con código 1 si algo no encaja: que el tipo está declarado y el estado es de los suyos; que hay un alcance y solo uno, y que su tipo lo admite; que están los campos que el tipo exige; que el estado y `ended_on` van juntos; que las fechas tienen orden (ni la previsión ni el final son anteriores al inicio, y el final no es posterior a la comprobación); que la línea está cargada, los dos nodos son suyos y van en el orden del kilometraje, o que el nodo suelto está en alguna línea cargada; y que las fuentes están en `sources.json`, la principal con URL. `oniel-data import annotations` carga el fichero en la tabla `annotations` (también lo hace `import all`, después de la red) y, si no encaja con la red cargada, lo rechaza sin tocar lo que había.

La API las sirve en `GET /api/annotations`, con `?kind=` (solo las de ese tipo; uno sin declarar da un 422) y `?on=AAAA-MM-DD` (solo las vigentes ese día), y dentro del índice (`GET /api/lines`), del detalle de cada línea y de `GET /api/network`, en `annotations`. La instantánea las lleva en `index.json` y en `lines/<id>.json`.

**`interruptions` queda solo como alias.** `GET /api/interruptions` (con `?date=`) responde lo mismo que `GET /api/annotations?kind=interrupcion`, y el índice, el detalle de línea y `GET /api/network` repiten en `interruptions` las anotaciones de ese tipo. Están para los visores anteriores: el visor se publica en Vercel antes de que Render termine de desplegar la API, y un visor abierto en el navegador sigue vivo tras un despliegue. Por lo mismo, el visor nuevo lee `interruptions` como anotaciones cuando una API anterior no trae `annotations`. Cuando no quede ninguno de los dos casos, el alias se retira. Los campos `interruptions` de los pasos por tramo, la simulación y los recorridos no son alias: son las anotaciones que cortan la circulación en ese tramo o recorrido ese día.

## Interrupciones del servicio

Los horarios GTFS son los planificados. Las interrupciones que Oniel conoce se registran a mano en `backend/data/curated/anotaciones.json`, una entrada de tipo `interrupcion` por interrupción (véase «Anotaciones de red»). El visor dibuja en rojo los tramos interrumpidos hoy, en el mapa y en el esquema; explica cada interrupción al seleccionar un tramo o un nodo, y añade una nota a los trenes que el horario sigue trayendo.

| Campo | Qué es |
|---|---|
| `id` | Identificador estable: línea, motivo y fecha de inicio. |
| `kind`, `status` | `interrupcion`, y `vigente` o `terminada`. |
| `line_id` | Línea cargada a la que afecta. |
| `from_node`, `to_node` | Nodos extremos, de esa línea y en el orden de su kilometraje. Afecta a todos los tramos que quedan entre ambos. |
| `start_date` | Primer día sin circulación. |
| `expected_end_date`, `expected_end_text` | Previsión de fin que publica la fuente, como fecha o como texto («otoño de 2027»). Opcionales: sin ellos, el visor dice que no hay fecha prevista. |
| `ended_on` | Día en que se reanudó la circulación. Sin él, la interrupción sigue vigente; con él, su estado es `terminada`. |
| `reason` | Motivo en una frase neutra. |
| `note` | Opcional: hasta dónde llegan los trenes, qué sigue en servicio, qué se sabe de la reanudación y según quién. |
| `source_ids` | Ids de `sources.json`. La primera es la fuente principal: la que se cita junto a la fecha («… (Adif)»). |
| `checked_on` | Día de la última comprobación en las fuentes. |

Una interrupción está vigente los días `start_date` ≤ día < `ended_on`. Al terminar no se borra: se le pone `ended_on` y el estado `terminada`, y queda como registro, y sigue marcando los trenes de las fechas en que estuvo vigente, por ejemplo al simular un cierre en una fecha pasada.

Se validan, se importan y se sirven como cualquier anotación (véase «Anotaciones de red»). Además, por ser un tipo que corta la circulación, cada una lleva su nota de horario (`schedule_note`), y los pasos por tramo, la simulación y los recorridos traen las vigentes en su día; cada fichero de tramo de la instantánea, las vigentes en el día de referencia.

### Interrupciones registradas

Comprobadas el 10 de noviembre de 2026. Lo que decía cada fuente ese día está resumido en `backend/data/raw/interrupciones/consultas_2026-11-10.json`: son avisos y paneles en tiempo real, sin histórico.

| Línea | De – a | Desde | Previsión de fin | Motivo | Fuente principal |
|---|---|---|---|---|---|
| Alta velocidad Madrid – Sevilla | Bifurcación La Sagra – Córdoba (6 tramos, 290,9 km) | 28 de octubre de 2026 | Sin fecha | Suspensión de la circulación tras el accidente del 28 de octubre de 2026 en el entorno de Urda | `adif-estado-de-la-red` |
| Convencional Madrid – Alcázar – Córdoba | Almuradiel-Viso del Marqués – Alcolea de Córdoba (9 tramos, 174,3 km) | 6 de septiembre de 2026 | Otoño de 2027 | Obras de adaptación a la autopista ferroviaria Algeciras–Madrid–Zaragoza | `adif-aviso-obras-autopista-ferroviaria` |

Cómo se fijaron los extremos:

- **Alta velocidad.** La página de estado de la red de Adif mantiene el aviso de que la circulación en la línea Madrid–Andalucía sigue interrumpida desde el accidente y da por abiertos los tramos Madrid–Toledo y Málaga–Sevilla. Los paneles de salidas de Ciudad Real dan por suspendidos todos los trenes de alta velocidad, también los que van a Puertollano, y en los de Córdoba no sale ninguno hacia Madrid, pero sí a Sevilla, Málaga y Granada. En Oniel eso deja abiertos Madrid – Bifurcación La Sagra y Córdoba – Sevilla, y sin circulación los seis tramos entre La Sagra y Córdoba. No hay fecha de reanudación: la nota de la entrada recoge la estimación del Ministerio de Transportes del 3 de noviembre de 2026, condicionada a una autorización judicial.
- **Línea convencional.** Las fuentes dan tres límites distintos por el norte. El aviso de Adif habla de servicio interrumpido entre Córdoba y Santa Cruz de Mudela; la información de Adif en prensa sitúa el corte de la vía entre Venta de Cárdenas y Algeciras; la nota de Renfe y los paneles de Santa Cruz de Mudela y Jaén dicen que los Media Distancia Madrid–Jaén hacen por carretera el trayecto entre Almuradiel y Jaén. Se registra lo que ve el viajero: los trenes llegan a Almuradiel-Viso del Marqués y no pasan de ahí. Por el sur, los paneles de Córdoba muestran trenes de Proximidad hasta Alcolea de Córdoba y el recorrido Córdoba–Jaén por carretera, así que el extremo es Alcolea. La fecha de inicio es la de la nota de Renfe; la previsión de fin es de Adif, recogida por la prensa, y no es un compromiso.

Límites de lo registrado:

- Entre Jaén y Córdoba ya se viajaba por carretera antes de las obras, por los daños de un temporal de enero de 2026, según la nota de Renfe. La prensa da fechas distintas para ese corte y un restablecimiento intermedio, y no se encontró una fecha en una fuente oficial: no tiene entrada propia, y los tramos entre Espelúy y Alcolea figuran sin circulación desde el 6 de septiembre de 2026 aunque no la tenían desde antes.
- Los 24 Intercity y Alvia Madrid-Atocha Cercanías – Andalucía del GTFS (válidos del 8 al 15 de noviembre de 2026) no figuran en los paneles de Ciudad Real del 10 de noviembre. Sus pasos por la alta velocidad entre Ciudad Real y Córdoba llevan la nota de la interrupción; los de la convencional entre Madrid y Manzanares y los de la línea de Manzanares a Ciudad Real no, porque esos tramos no están interrumpidos. Oniel no sabe si circulan.
- Una interrupción es de todo el servicio entre dos nodos y por días completos. No se registran reducciones de frecuencia, limitaciones de velocidad ni cortes de unas horas.

### Cómo se actualiza

No hay actualización automática: Adif no publica estos avisos como datos abiertos y su web rechaza las descargas automáticas. Lo revisa quien mantiene Oniel, o una sesión a petición suya.

Cada cuánto: una vez por semana mientras haya alguna interrupción sin fecha de fin (hoy, la de la alta velocidad); una vez al mes si todas tienen una previsión lejana; y siempre que una fuente anuncie un cambio (una reanudación, otra previsión, un corte nuevo) o se refresque el GTFS.

Lo recuerda un flujo de GitHub Actions, `.github/workflows/recordatorio-interrupciones.yml`. Cada día a las 07:00 UTC (y a mano, desde la pestaña Actions) lee `anotaciones.json` y, si alguna interrupción sin `ended_on` tiene un `checked_on` de más de siete días, abre la incidencia «Revisar las interrupciones del servicio», con la etiqueta `revision-interrupciones` y la lista de entradas pendientes. Mientras haya una abierta con esa etiqueta no abre otra, así que la PR de la revisión debe cerrarla. El flujo solo lee el fichero: no consulta ninguna fuente ni cambia ningún dato. Como se ejecuta a diario, el aviso llega al octavo día desde la última revisión.

1. Consultar las fuentes de cada entrada: el estado de la red y los avisos de Adif, la sala de prensa de Renfe y los paneles de salidas y llegadas de las estaciones de los extremos.
2. Resumir lo consultado, con palabras propias, en `backend/data/raw/interrupciones/consultas_<fecha>.json`, y poner al día `sources.json` (`retrieved_on`, `file` y las fuentes nuevas que hagan falta).
3. Editar `anotaciones.json`. `checked_on` cambia siempre. Si la circulación se reanudó, se pone `ended_on` y el estado pasa a `terminada`; si cambió la previsión, se corrige; si hay otro corte, se añade una entrada. Si un corte se reabre solo en parte, se acortan sus extremos o se divide en dos entradas. No se infiere nada: lo que la fuente no dice, no se escribe.
4. `uv run oniel-data validate`, `uv run oniel-data import all` (regenera la instantánea) y las pruebas. La tabla de arriba se pone al día en la misma PR.
5. Al fusionar, Render reimporta la base. La instantánea va dentro del visor, así que hay que publicarlo (`docs/despliegue.md`): hasta entonces, quien entre con la API dormida ve la interrupción anterior.

Las pruebas fijan como «hoy» el 10 de noviembre de 2026, el día en que las dos entradas iniciales estaban vigentes. Ponerles `ended_on` o cambiar su previsión no las rompe; cambiar sus extremos o su fecha de inicio, sí, y entonces se corrigen en la misma PR.

## Conjuntos de datos

Cada fichero de horarios importado es un conjunto de datos: se guarda con su fuente, su operador, el día en que se descargó y los días que cubre, y los servicios cuelgan de él. Importar un fichero nuevo no borra el anterior, de modo que se puede cargar más de un operador a la vez y comparar más adelante cómo cambia el servicio.

Los ficheros se declaran en la lista `feeds` de `backend/data/curated/sources.json`, del más antiguo al más reciente:

```json
{ "file": "raw/renfe/google_transit_av_ld_md_2026-11-08.zip", "source_id": "renfe-gtfs-av-ld-md", "operator_id": "renfe", "retrieved_on": "2026-11-08" }
```

| Conjunto | Fuente | Operador | Descargado | Cubre |
|---|---|---|---|---|
| `renfe-gtfs-av-ld-md-2026-11-08` | `renfe-gtfs-av-ld-md` | Renfe | 2026-11-08 | del 7 de noviembre de 2026 al 29 de septiembre de 2027 |
| `ouigo-gtfs-nap-2026-11-12` | `ouigo-gtfs-nap` | Ouigo | 2026-11-12 | del 26 de junio al 12 de diciembre de 2026 |

Una entrada de `feeds` admite además `product` (el nombre con el que se rotulan todos los trenes del fichero) y `stop_id_prefix` (un prefijo que se quita de sus códigos de parada); las usa el fichero de Ouigo.

Cómo se decide qué se muestra:

- El conjunto **vigente** de una fuente es el descargado más recientemente. De los vigentes salen el día de referencia y las cifras de la cobertura. Con varios vigentes, uno por operador, se toman los días que cubren todos a la vez, del comienzo más tardío al final más temprano (hoy, del 7 de noviembre al 12 de diciembre de 2026); el día de referencia es el laborable con más servicios de los primeros treinta de esos días, y así tiene los trenes de todos los operadores. `validate` avisa si los ficheros vigentes no coinciden en ningún día.
- El conjunto **activo** de una fuente en un día es el más reciente cuya validez incluye ese día. Los trenes de un tramo, las paradas de una estación, los recuentos y la simulación de un día leen solo los conjuntos activos ese día. `GET /api/coverage` los enumera en `datasets`.
- Se decide por fuente, no por operador: un operador puede publicar ficheros que no se sustituyen entre sí (alta velocidad y cercanías, por ejemplo). Hoy cada operador con horarios tiene una sola fuente y da lo mismo.

Cómo se importa:

- `import gtfs` reconoce cada fichero por su SHA-256. Si ya está, rehace sus servicios (las reglas de recorrido pueden haber cambiado) sin duplicar nada; si es nuevo, crea su conjunto y deja los demás como están.
- `import all` importa todos los ficheros de `feeds` y trata la lista como la referencia: reimportar la red borra los pasos por tramo de todos los conjuntos, así que retira de la base el conjunto que ya no esté declarado. El histórico se conserva mientras el fichero siga en `backend/data/raw/` y en `feeds`.
- Cada fichero añade a `import all` el tiempo de leerlo y resolverlo (en local, unos 6 s por fichero de Renfe, medido el 11 de noviembre de 2026; en el plan gratuito de Render, bastante más). Conviene tenerlo en cuenta al acumular histórico.

Para añadir un horario más reciente: guardar el zip en `backend/data/raw/<operador>/` con el día de descarga en el nombre, añadirlo a `feeds` (y poner al día `retrieved_on`, cobertura y notas de su fuente), ejecutar `validate` e `import all` y subir la instantánea. Con el de Renfe, los tres primeros pasos los hace `oniel-data refresh gtfs` (véase «Refresco de los horarios»). Los recuentos de las pruebas no cambian: usan siempre el fichero de Renfe del 8 de noviembre de 2026 y el de Ouigo del 12 de noviembre de 2026 por su nombre (`backend/tests/conftest.py`).

La instantánea estática lleva solo el estado actual. Para la evolución futura guarda además `frontend/public/data/historico/<conjunto>/segment-counts.json`: los pasos por tramo de cada conjunto en su propio día de referencia. Pesa 2,8 KB por conjunto con los 39 tramos de hoy (medido el 11 de noviembre de 2026), y el visor todavía no lo lee.

### Refresco de los horarios

El fichero de Renfe se refresca solo; el de Ouigo, a mano.

**Renfe.** El flujo `.github/workflows/gtfs.yml` se ejecuta los lunes a las 06:30 UTC, y a mano desde la pestaña Actions («Refresco del GTFS» → Run workflow). Hace esto:

1. Descarga el fichero publicado. Parte de la URL registrada en `sources.json`, la página del conjunto en data.renfe.com, que es un portal CKAN: su ficha (`/api/3/action/package_show`) da la dirección del zip.
2. Lo compara con los ficheros de Renfe ya declarados. Si el horario es el mismo, termina sin abrir nada.
3. Si es nuevo, `oniel-data refresh gtfs` lo guarda en `backend/data/raw/renfe/google_transit_av_ld_md_<fecha>.zip`, lo añade al final de `feeds` y pone al día la fuente (`file`, `retrieved_on` y las frases de validez y de publicación) y las dos tablas de este documento que lo nombran. El fichero anterior sigue declarado.
4. Ejecuta `validate`, `import all` (que regenera la instantánea), `pytest` y las pruebas Playwright sobre la instantánea nueva.
5. Abre una PR en la rama `datos/gtfs-<fecha>`, con la etiqueta `refresco-gtfs`, que resume la validez, los viajes por línea y los pasos por tramo que cambian, y lanza el CI sobre esa rama.

El flujo no fusiona nada. Fusionar publica los horarios, y eso lo decide quien revisa la PR.

Para no llenar el correo, abre como mucho una PR por horario nuevo. Si no hay cambios no abre nada. Mientras haya una PR con la etiqueta `refresco-gtfs` abierta, no descarga ni abre otra: la siguiente ejecución tras fusionarla o cerrarla recoge lo que haya publicado entonces.

Se compara el contenido, no el zip. Renfe sirve su fichero desde varios servidores y cada uno tiene su propio zip, con los mismos ficheros dentro y otros bytes: el 12 de noviembre de 2026, cuatro descargas seguidas dieron tres SHA-256 distintos y un contenido idéntico. Por eso `refresh gtfs` calcula el SHA-256 de los nombres y los bytes de los ficheros ya descomprimidos (`content_sha256`) y lo compara con el de cada fichero declarado. La tabla `datasets` sigue guardando el SHA-256 del zip tal como se descargó.

Renfe vuelve a generar el fichero cada noche y quita los días pasados, así que casi cada lunes el horario es distinto del cargado aunque no cambie ningún tren: lo normal es una PR por semana. Si resulta demasiado, basta cambiar el `cron` del flujo. Cada fichero pesa unos 0,7 MB en el repositorio y alarga `import all`; para retirar uno antiguo se borra de `feeds` y de `backend/data/raw/` y se vuelve a ejecutar `import all`, que retira su conjunto de la base.

Por qué la PR no llega en rojo. Las pruebas de `pytest` leen siempre los dos ficheros fijos de `backend/tests/conftest.py`, así que sus recuentos no cambian con un fichero nuevo. Las de Playwright sí leen la instantánea regenerada, y `validate` puede fallar con una parada sin asignar o con una regla de recorrido que ya no encaja con ningún viaje. Por eso el flujo pasa todo antes de abrir la PR. Si algo falla termina en rojo, no abre la PR y abre la incidencia «El fichero nuevo de horarios de Renfe no pasa las comprobaciones», una sola mientras siga abierta, con el enlace a la ejecución.

El CI de esa PR. GitHub retiene los flujos de `pull_request` de una PR que abre otro flujo con su token: en la PR aparece el aviso «Approve workflows to run» y `Backend` y `Frontend` no se ejecutan como comprobaciones suyas hasta que quien la revisa lo pulsa. Para no depender de ese clic, el flujo lanza además el CI sobre la rama (`gh workflow run ci.yml --ref datos/gtfs-<fecha>`): su resultado queda en el commit y en la pestaña Actions, aunque la lista de comprobaciones de la PR no lo enseñe. Así ocurrió en la primera ejecución, el 12 de noviembre de 2026 (PR 71): el CI lanzado pasó, y al aprobar el retenido pasó también, ya dentro de la PR.

La PR lleva la instantánea regenerada, así que entra en conflicto con `main` si entre tanto se fusiona otra PR que también la regenere. Lo más sencillo entonces es cerrarla sin fusionar, borrar su rama y lanzar el flujo a mano: abre otra con lo publicado ese día sobre el `main` actual.

A mano, lo mismo en local:

```bash
cd backend
uv run oniel-data refresh gtfs      # descarga, compara y, si cambió, declara el fichero
uv run oniel-data validate
uv run oniel-data import all        # regenera la instantánea
```

`refresh gtfs --file <zip>` usa un fichero ya descargado y `--date` fija el día de descarga.

**Ouigo.** Su fichero queda manual. El Punto de Acceso Nacional exige iniciar sesión con una cuenta de usuario para descargar, y Oniel no guarda credenciales de nadie, tampoco como secreto de GitHub: no hay una cuenta del proyecto, solo personales. Se descarga con la sesión iniciada en el navegador (conjunto 1515), se guarda en `backend/data/raw/ouigo/gtfs_ouigo_<fecha>.zip` y se sigue «Para añadir un horario más reciente», copiando `product` y `stop_id_prefix` de la entrada anterior de `feeds`.

Para que no se pase la fecha, el mismo flujo ejecuta cada semana `oniel-data refresh expiring`: si a un fichero vigente que no se refresca solo le quedan 21 días o menos de validez, abre la incidencia «Descargar a mano los horarios que están a punto de caducar», una sola mientras siga abierta. Si la validez termina sin relevo, los ficheros vigentes dejan de coincidir en algún día, `validate` falla y el refresco de Renfe tampoco abre su PR.

## Destinos directos

La ficha de una estación dice a qué otras estaciones se llega desde ella sin cambiar de tren el día de referencia: cuántos trenes, de qué tipo de servicio, de qué operador y entre qué horas salen. Sale de los horarios ya importados (`services`, `service_stops`, `service_dates`), sin ninguna fuente nueva.

**Cómo se cuenta** (`services_repo.destinations_from_node`). De cada tren que para en el nodo ese día, en los conjuntos de datos activos, se toman sus paradas posteriores y se agrupan por destino: el nodo de la red, si la parada está en ella, o la parada del fichero de horarios, con su nombre, si no lo está (Málaga, Badajoz, Alicante). Cada tren cuenta una vez por destino. La lista va del destino con más trenes al que menos y, a igualdad, por nombre. De cada destino se guardan los tipos de servicio y los trenes de cada operador, del que más tiene al que menos, y la primera y la última salida del nodo.

**Subir y bajar.** El fichero de horarios marca las paradas en las que un tren solo deja viajeros (`pickup_type` 1) o solo los recoge (`drop_off_type` 1), y hay que respetarlo: un tren al que no se puede subir aquí, o del que no se puede bajar allí, no une las dos estaciones. No son solo las cabeceras: el 13 de noviembre de 2026 pasan por Ciudad Real 23 trenes hacia Madrid, pero 11 de ellos (diez Intercity de Málaga y Sevilla a Madrid-Atocha Cercanías y un Alvia de Cádiz) solo dejan viajeros allí, así que a Madrid se puede ir en 12. En sentido contrario pasa lo mismo: de 21 trenes de Madrid que paran en Ciudad Real, sirven 11. Las paradas de cada nodo (`calls`) llevan por eso dos campos, `boards` y `alights`.

**El mismo número que el comparador.** El comparador de recorridos cuenta los trenes directos entre dos estaciones en el cliente, con las paradas de los dos nodos; desde esta tarea aplica el mismo criterio de subida y bajada. Una prueba recorre todos los pares de nodos de la red y exige que las dos cuentas coincidan (`test_direct_destinations_match_the_route_comparator`).

**Qué trenes faltan.** Solo se importan los trenes que recorren alguna de las líneas cargadas, así que en una estación de la que salen otras líneas (Madrid, Córdoba, Sevilla, Alcázar de San Juan) no están los destinos de los trenes que no pisan las cargadas: de Madrid-Puerta de Atocha no sale Barcelona. Tampoco están los trenes de Iryo, que no publica sus horarios. Y son horarios publicados: una interrupción vigente no descuenta trenes. La ficha dice las tres cosas.

**Dónde viaja.** En `GET /api/nodes/{id}/services` (campo `destinations`, con `?date=` para otro día) y en `nodes/<id>.json`, que el visor ya pedía al abrir la ficha de la estación: el arranque no cambia. Medido el 12 de noviembre de 2026, la carpeta `nodes/` pasa de 300 a 484 KB en disco; el fichero mayor, el de Córdoba (62 destinos), lleva 13,7 KB de destinos y se descarga en 5,2 KB con gzip.

**Destinos fuera de la red.** Se nombran, sin enlace. Sus coordenadas están en la base (`stop_mappings` guarda las de `stops.txt` de todas las paradas de los trenes importados), pero no se exportan: nada las dibuja todavía.

Recuentos que comprueban las pruebas, con los ficheros fijos y el 13 de noviembre de 2026: Ciudad Real tiene 49 destinos directos, 14 de ellos en la red (Córdoba 20 trenes, Madrid-Puerta de Atocha 12, Sevilla-Santa Justa 12, Puertollano 11); de Madrid-Puerta de Atocha a Córdoba hay 55 trenes, 49 de Renfe y 6 de Ouigo.

## Instantánea estática

`oniel-data import all` (o `export snapshot`) deja en `frontend/public/data` todo lo que el visor necesita sin API. La red va por partes, para que el arranque no pese más cada vez que se añade una línea:

| Fichero | Qué lleva | Cuándo lo pide el visor |
|---|---|---|
| `index.json` | El índice de toda la red: las líneas, todos los nodos sin sus textos, los tramos con sus datos y la geometría simplificada, las conexiones a trazos y las anotaciones de red (con `interruptions` como alias temporal). | Al arrancar. |
| `lines/<id>.json` | El detalle de una línea: sus nodos con descripción y detalles, sus tramos con la geometría completa, sus conexiones, sus anotaciones y los pasos por tramo del día de referencia. | Al abrir la línea, al seleccionar un tramo o un nodo suyo (también por enlace directo) o al acercar el mapa a ella (zoom 8 o más). |
| `coverage.json` | Cobertura, conjuntos de datos y fuentes. | Al arrancar. |
| `segments/<id>.json`, `nodes/<id>.json` | Los trenes de un tramo y, de una estación, sus paradas y sus destinos directos el día de referencia (véase «Destinos directos»). | Al abrir su ficha. |
| `historico/<conjunto>/segment-counts.json` | Pasos por tramo de cada conjunto de datos (véase «Conjuntos de datos»). | Todavía no se lee. |

La red entera en un solo fichero (`network.json`, con `segment-counts.json`) dejó de exportarse el 11 de noviembre de 2026: el visor ya no la descargaba y las pruebas del grafo de rutas leen el índice.

La API ofrece lo equivalente: `GET /api/lines` (el índice) y `GET /api/lines/{id}` (el detalle, con `?date=` para los recuentos de otro día). `GET /api/network` sigue devolviendo la red entera.

Qué va en el índice y por qué. Lleva todos los nodos y todos los tramos, no solo los principales: con ellos el buscador encuentra cualquier estación, un enlace directo a cualquier tramo o nodo sabe de qué línea es antes de pedirla, y el cálculo de recorridos en el cliente tiene el grafo entero (nodos, tramos, longitudes y velocidades) sin descargar ninguna línea. Lo que se deja fuera es lo que pesa: la geometría completa y los textos de los nodos. La geometría del índice se simplifica con una tolerancia de 200 m (Douglas-Peucker, `oniel.geo.simplify`, `INDEX_TOLERANCE_M`); los extremos de cada tramo no se mueven. Hasta el zoom 8 un píxel del mapa son más de 230 m, así que el trazo simplificado y el completo se dibujan igual; al acercarse más, el visor ya ha pedido la línea y sustituye su geometría por la completa. Los recuentos de cada línea llevan el máximo de toda la red (`network_max_count`) para que las barras del esquema tengan la misma escala en todas las líneas.

En el visor, `frontend/src/data/api.ts` pide el índice y cada línea (una sola vez por origen, con caché en memoria) y `frontend/src/data/network.ts` compone con ello la red que usan el mapa y el panel. Las cabeceras de caché de `frontend/vercel.json` para `/data/` cubren los ficheros nuevos.

### Medidas

Medido el 11 de noviembre de 2026 con las tres líneas (976 km, 42 nodos, 39 tramos); gzip con nivel 9.

Antes, el arranque descargaba `network.json` y `segment-counts.json`:

| Fichero | Bruto | gzip |
|---|---|---|
| `network.json` | 376,2 KB | 106,5 KB |
| `segment-counts.json` | 2,5 KB | 0,6 KB |

El 83 % de `network.json` era geometría (311 KB brutos), y casi la mitad de ella (`line_features`, 145 KB) repetía la de los tramos sin que el visor la usara. Lo que aportaba cada línea (su ficha, nodos, tramos y geometrías, comprimido aparte):

| Línea | Bruto | gzip |
|---|---|---|
| Alta velocidad Madrid – Sevilla (470,5 km) | 142,0 KB | 43,6 KB |
| Convencional Madrid – Alcázar – Córdoba (440,7 km) | 190,5 KB | 53,6 KB |
| Convencional Manzanares – Ciudad Real (64,4 km) | 16,2 KB | 3,2 KB |

Ahora el arranque descarga `index.json`, y cada línea se descarga cuando hace falta:

| Fichero | Bruto | gzip |
|---|---|---|
| `index.json` | 54,4 KB | 11,0 KB |
| `lines/lav-madrid-sevilla.json` | 84,1 KB | 25,5 KB |
| `lines/convencional-madrid-alcazar-cordoba.json` | 119,2 KB | 32,0 KB |
| `lines/manzanares-ciudad-real.json` | 11,3 KB | 3,3 KB |

En el índice, cada línea aporta entre 1,3 KB (Manzanares – Ciudad Real) y 5,1 KB (la convencional por Alcázar) comprimidos; la geometría simplificada de toda la red son 359 vértices frente a 6.142.

Proyección, suponiendo líneas como la media de hoy (325 km y 13 tramos; cien líneas así serían unos 32.500 km, el doble de la red española, de modo que es una cota alta):

| Líneas | Arranque antes (gzip) | Arranque ahora (gzip) |
|---|---|---|
| 3 (hoy) | 107 KB | 11 KB |
| 20 | 0,7 MB | 73 KB |
| 100 | 3,6 MB | 365 KB |

El índice crece unos 3,7 KB comprimidos por línea, diez veces menos que antes. Si llega a pesar, lo siguiente es quitar de sus tramos los nombres de los extremos, que ya están en los nodos, y servir las conexiones con cada línea. Un límite conocido: `GET /api/lines` simplifica la geometría en cada petición (unos 30 ms con tres líneas); con muchas líneas convendrá guardarla ya simplificada al importar.

La vía no espera al mapa base: se añade al mapa en cuanto el estilo está listo (`style.load` en `frontend/src/map/MapView.tsx`), sin aguardar a las teselas y los rótulos de OpenFreeMap. Medido el 12 de noviembre de 2026 con un Pixel 7 emulado, la caché vacía y el procesador ralentizado cuatro veces, tres pasadas por caso: con 4G lenta (1,6 Mbit/s, 150 ms) la vía pasa de dibujarse a los 8,1 – 8,3 s a los 4,8 – 5,1 s, y con 3G (400 kbit/s, 400 ms), de 25,3 – 25,4 s a 15,8 – 16,3 s; en producción, ya con el cambio, 5,0 – 5,3 s y 16,1 – 16,3 s, antes de que llegue la primera tesela (6,4 s y 23,7 s). Una primera medida del día 11, con el equipo ocupado por otras tareas, dio cifras más altas y dispares: estas pruebas hay que hacerlas con el equipo libre. Lo que queda por delante es sobre todo el JavaScript del visor (376 KB).

El JavaScript va en dos ficheros. MapLibre es tres cuartas partes del total (295 de 380 KB comprimidos; React son 68 y el visor, 20) y no se puede adelgazar, así que se carga aparte con un `import()` (`MapView` en `frontend/src/app/App.tsx`) y `index.html` lo precarga con `modulepreload` (el complemento `precargarMapa` de `frontend/vite.config.ts`), para que se descargue a la vez que el resto. El panel ya no lo espera: medido el 12 de noviembre de 2026 con el mismo móvil emulado, la lista de líneas pasa de verse a los 4,7 – 6,5 s a los 1,8 – 2,1 s con 4G lenta, y de 13,8 – 14,0 s a 6,0 – 6,2 s con 3G; la vía se dibuja cuando antes (unos 16 s con 3G). La hoja de estilos de MapLibre se queda en la principal (`frontend/src/main.tsx`): si se cargara con el mapa llegaría después que la del visor y anularía sus reglas (el mapa quedaba con altura cero).

La vía tampoco espera a las tipografías del mapa base, aunque aparezca casi a la vez que los rótulos. Comprobado en producción el 12 de noviembre de 2026 con el mismo móvil emulado y 4G lenta, dos pasadas por caso: con las tipografías de OpenFreeMap sin tocar la vía se dibuja a los 4,9 – 6,4 s; retrasándolas 5 s, a los 4,9 – 5,2 s; retrasándolas 10 s, a los 5,0 – 5,1 s, y bloqueándolas del todo, a los 5,3 – 5,6 s. El mapa las pide hacia los 4,2 s, cuando el estilo termina de cargar, que es también cuando se añade la vía: de ahí la coincidencia. Lo que marca esos 5 s es lo que va antes, la descarga de MapLibre y del estilo.

## Modelo de datos

Pensado para añadir líneas, operadores y medios de transporte sin rehacer la aplicación.

- `sources`: procedencia, licencia, fecha, cobertura y checksum.
- `operators`: operadores y administradores de infraestructura. De un operador de trenes, `timetable` dice si sus horarios están cargados o no los publica.
- `line_operators`: qué operadores de trenes circulan por cada línea, tengan o no horarios cargados.
- `lines`: una línea por fila, con `mode` (`ferrocarril` hoy; mañana `metro`, `autobús`…), administrador, ancho, electrificación, orden de presentación (`sort_order`) y geometría completa.
- `nodes` + `line_nodes`: los nodos son independientes de la línea; `line_nodes` da su kilómetro y orden en cada línea, así un nodo puede pertenecer a varias líneas (Madrid-Puerta de Atocha y Córdoba lo hacen). `rank` distingue los nodos principales de los secundarios, que el visor atenúa y oculta en el esquema compacto.
- `segments`: tramos entre nodos consecutivos con geometría, velocidad máxima y habitual, número de vías (`tracks`) y la fuente de su geometría.
- `connections`: hacia dónde continúa la red donde Oniel todavía no tiene datos (se dibujan a trazos).
- `stop_mappings`: cómo se resuelve cada parada de un horario contra la red. La tabla es común a todas las líneas; una parada asignada a un nodo por una línea no la degrada otra que la declare como salida. Las reglas de recorrido (`route_overrides` de cada especificación) no se guardan en la base: solo actúan al importar.
- `datasets`: un conjunto de datos por fichero de horarios importado, con su fuente, su operador, el fichero, su SHA-256, el día de descarga (`retrieved_on`), los días que cubre (`valid_from`, `valid_to`) y cuándo se importó. El id es legible: la fuente y el día de descarga (`renfe-gtfs-av-ld-md-2026-11-08`).
- `services`, `service_dates`, `service_stops`: horarios por tren y día, con el operador y el conjunto de datos del que salen (`dataset_id`, que forma parte de la clave). Cada viaje del GTFS se guarda una sola vez por conjunto aunque recorra varias líneas, y el mismo viaje puede estar en varios conjuntos.
- `service_segment_passes`: el paso de cada tren por cada tramo, precalculado con las reglas de simulación, línea a línea y por conjunto de datos. Un tren que cambia de línea tiene pasos en cada una solo entre las paradas que le corresponden.
- `annotations`: anotaciones de red (hoy, las interrupciones del servicio), con su tipo, su estado, su alcance (de un nodo a otro de una línea, un nodo o una geometría propia), sus fechas, el título o el motivo, las fuentes y el día de la última comprobación. Los tramos afectados no se guardan: salen del orden de los dos nodos en `line_nodes`, de modo que reimportar la red no las deja huérfanas. El tipo y el estado son texto y los comprueba la importación contra los tipos declarados, así que un tipo nuevo no necesita migración. Sustituye a la tabla `interruptions`, que la migración `0007` traslada y retira.
- `import_runs`: historial de importaciones con estadísticas.

## Añadir otra línea

1. Descargar la geometría cruda a `backend/data/raw/` con fecha en el nombre y registrar la fuente en `sources.json`. Si la relación OSM trae las dos vías o miembros desordenados, usar `geometry_source.parts` (relación + punto inicial y final de cada parte); si es una relación limpia, basta `file` + `relation_id`.
2. Escribir `backend/data/curated/<línea>.json` con la línea (`sort_order` para el orden en el visor, `tracks` por defecto; `description` en párrafos separados por una línea en blanco, el primero breve porque el visor lo muestra de entrada y pliega el resto, sin repetir longitud, velocidad, ancho ni electrificación, que ya salen en la ficha), sus nodos (coordenadas o kilómetro; `rank: "secundario"` para los menores; `shared: true` para una estación que ya define otra línea), `track_sections` donde cambie el número de vías, las conexiones y la asignación de paradas. Si los puntos kilométricos de la línea no empiezan en cero, `pk_origin_km` lleva el PK de su origen y los `reference_pk_km` de los nodos se escriben tal como los da Adif. En `corridor_filter`, `min_node_stops` y `any_of_stop_ids` evitan que entren trenes de líneas paralelas. Una parada que es nodo de otra línea cargada se asigna como salida con `via` (la línea y el nodo por el que se entra en ella; una lista si el camino cruza más de una). Si un tren recorre esta línea solo en parte y sigue por otra cargada, o la cruza sin parar en ella, declararlo en `route_overrides` (paradas seguidas que lo identifican, tramo de paradas que va por esta línea y, si hace falta, asignaciones propias de esos viajes). Si la línea nueva sustituye a una conexión a trazos de otra especificación, retirarla de allí.
3. Añadir el id de la línea a `line_ids` en `backend/src/oniel/settings.py` (la primera línea de la lista define los nodos compartidos).
4. `uv run oniel-data validate --spec data/curated/<línea>.json` hasta que no haya problemas.
5. `uv run oniel-data import network` e `import gtfs` (sin `--spec` cargan todas las líneas; `import all` hace todo y exporta la instantánea).

6. Subir con la PR la instantánea regenerada: `index.json` lleva la línea nueva y aparece su `lines/<id>.json`. Si la línea es larga, anotar en «Medidas» de «Instantánea estática» lo que pesan ahora el índice y su fichero.

El visor dibuja todo lo que trae el índice (`index.json` o `GET /api/lines`): todas las líneas en el mapa y una entrada por línea en la lista de la vista de la red. No hay que tocar el visor: el detalle de la línea nueva se pide solo cuando se abre.
