# Datos de Oniel: procedencia, licencias y modelo

## Fuentes de esta versión

| Id | Qué aporta | Editor | Licencia | Fecha de consulta |
|---|---|---|---|---|
| `renfe-gtfs-av-ld-md` | Horarios de alta velocidad, larga distancia y media distancia de Renfe (GTFS) | Renfe Viajeros, data.renfe.com | CC BY 4.0 | 2026-11-08 |
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
| `openfreemap` | Mapa base del visor | OpenFreeMap · OpenMapTiles · OSM | ODbL / BSD | 2026-11-08 |

El registro completo, con URL, cobertura y notas, está en `backend/data/curated/sources.json` y se sirve en `GET /api/sources`. Los ficheros crudos están en `backend/data/raw/` con fecha en el nombre; su SHA-256 se guarda en la tabla `sources` al importar. Los ficheros de horarios se declaran además en la lista `feeds` del mismo `sources.json`, uno por descarga (véase «Conjuntos de datos»). Las seis fuentes del 10 de noviembre de 2026 son las de las interrupciones del servicio: avisos, paneles y noticias que cambian, de modo que su fichero crudo es un registro de lo que decían ese día (`raw/interrupciones/consultas_2026-11-10.json`), resumido y sin copiar el texto.

## Líneas cargadas

| Línea | Id | Longitud medida | Nodos | Tramos | Viajes del GTFS |
|---|---|---|---|---|---|
| Alta velocidad Madrid – Sevilla (Adif 010) | `lav-madrid-sevilla` | 470,5 km | 12 | 11 | 335 (AVE, AVLO, Alvia, Intercity) |
| Convencional Madrid – Alcázar de San Juan – Córdoba (Adif 300 y 400) | `convencional-madrid-alcazar-cordoba` | 440,7 km | 26 (2 compartidos) | 25 (11 de vía única) | 503 (MD, Regional Exprés, Proximidad, Alvia, Intercity) |
| Convencional Manzanares – Ciudad Real (Adif 522) | `manzanares-ciudad-real` | 64,4 km | 4 (2 compartidos) | 3 (los 3 de vía única) | 154 (MD, Regional Exprés, Intercity, Alvia) |

En «compartidos» se cuentan los nodos que define otra línea. Son 975,6 km de red, 30 estaciones y 814 viajes distintos, porque un viaje que recorre varias líneas cuenta en cada una y se guarda una sola vez:

- Madrid-Puerta de Atocha y Córdoba son comunes a la alta velocidad y a la convencional: la red forma un lazo Madrid–Córdoba con dos recorridos, el de alta velocidad (343,6 km) y el convencional (440,7 km).
- Manzanares (de la convencional) y Ciudad Real (de la alta velocidad) son los extremos de la tercera línea, que cierra un segundo lazo: de Madrid a Ciudad Real hay 170,8 km por la alta velocidad y 260,5 km por la convencional hasta Manzanares (196,1 km) y la línea de Manzanares a Ciudad Real (64,4 km).
- Los 130 MD y Regional Exprés de la línea de Manzanares a Ciudad Real vienen de Alcázar de San Juan o siguen hacia allí, así que ya estaban en la convencional, donde cuentan solo hasta Manzanares.
- 24 Intercity y Alvia Madrid-Atocha Cercanías – Andalucía recorren las tres líneas (la convencional hasta Manzanares, la tercera entera y la alta velocidad desde Ciudad Real) y cuentan en las tres.

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
- **Servicios incluidos.** El GTFS de Renfe trae AVE, AVLO, Avant, Alvia, Intercity, Euromed, MD, Regional Exprés, Regional y Proximidad, pero no Cercanías: los trenes de la línea C-3 Madrid–Aranjuez no aparecen, y tampoco los de otros operadores ni mercancías.
- **Selección de viajes.** Un viaje se asigna a la línea convencional si para en al menos dos de sus nodos y en alguna de las estaciones que no comparte con la alta velocidad (`min_node_stops` y `any_of_stop_ids` del filtro de corredor). Así entran los MD Madrid–Jaén, Madrid–Alcázar–Albacete, Alcázar–Ciudad Real–Badajoz, Córdoba–Jaén y Cádiz–Jaén, el Alvia Barcelona–Córdoba por Alcázar y los trenes de Proximidad de Córdoba. A la línea de Manzanares a Ciudad Real se asigna el que para en al menos dos de sus cuatro estaciones, porque entre ellas no hay otro recorrido: son 130 viajes, MD y Regional Exprés de Alcázar de San Juan, Madrid, Albacete, Alicante o Valencia a Ciudad Real y Badajoz, y todos paran en las cuatro. Los Intercity y Alvia Madrid-Atocha Cercanías–Córdoba–Sevilla/Málaga/Algeciras del fichero (24 viajes, válidos del 8 al 15 de noviembre de 2026) no pasan ninguno de los dos filtros, porque solo paran en Madrid, Ciudad Real y Córdoba, y entran por una regla de recorrido (véase el apartado siguiente).
- **Trenes que cambian de línea.** Esos 24 viajes son los horarios publicados por Renfe tras la interrupción de la alta velocidad en Urda: tardan 2 h 50 entre Madrid y Ciudad Real, compatible solo con ir por la red convencional (Aranjuez, Alcázar de San Juan, Manzanares y la línea de Manzanares a Ciudad Real), y 1 h 15 entre Ciudad Real y Córdoba, solo posible por la alta velocidad. Cada especificación los declara en `route_overrides`: una regla encaja con los viajes que llevan ciertas paradas seguidas (`consecutive_stop_ids`, en ese orden o en el inverso) y dice entre qué paradas el viaje va por esa línea (`from_stop_id`, `to_stop_id`) y qué asignaciones de parada cambian solo para ellos. La convencional los resuelve entre Madrid y Ciudad Real, saliendo por Manzanares; la de Manzanares a Ciudad Real, entre las mismas paradas, entrando por Manzanares; la LAV, desde Ciudad Real. Los 4 Alvia que no paran en Ciudad Real (Madrid–Córdoba en las mismas 3 h 45) se tratan igual: para ellos Córdoba es salida por Manzanares en la convencional y salida por Ciudad Real en la tercera línea, que cruzan sin parar, y Madrid-Atocha Cercanías es entrada por Ciudad Real en la LAV.
- **Paradas que están en otra línea cargada.** Una asignación con `via` indica que la parada es un nodo de otra línea y por dónde se llega a ella: la línea y el nodo por el que el tren entra. Si el camino cruza más de una línea, `via` es una lista, un trecho por línea (de Manzanares a Córdoba: la línea de Manzanares a Ciudad Real y, desde Ciudad Real, la alta velocidad). El reparto de tiempos usa entonces los kilómetros por esas líneas en vez de la línea recta, y el visor explica por dónde sigue el tren. Las asignaciones generales también lo usan: Daimiel, Almagro y Ciudad Real son, para la convencional, salidas por Manzanares hacia la tercera línea, y Alcázar de San Juan o Madrid son, para la tercera, salidas por Manzanares hacia la convencional. Así los 24 trenes desviados aparecen en los tramos Madrid–Manzanares de la convencional, en los tres de la línea de Manzanares a Ciudad Real y en Ciudad Real–Córdoba de la alta velocidad, y en ningún otro. `oniel-data validate` avisa si una regla deja de encajar con algún viaje del GTFS o si un `via` no se puede seguir (una línea que no está cargada, un nodo de enlace que no es común a las dos líneas, una parada que no es nodo de la última).
- **Estaciones compartidas.** Madrid-Puerta de Atocha agrupa en un solo nodo la estación de alta velocidad (60000) y Madrid-Atocha Cercanías (18000), de donde salen los trenes convencionales: forman el mismo complejo. La tabla `stop_mappings` asigna 18000 al nodo, de modo que esos trenes aparecen en «Trenes que paran aquí». Ciudad Real es una sola estación para la alta velocidad y para la línea de Manzanares: su nodo lo define la LAV y la tercera línea lo incorpora con `shared: true`, igual que hace con Manzanares, que define la convencional.

## Interrupciones del servicio

Los horarios GTFS son los planificados. Las interrupciones que Oniel conoce se registran a mano en `backend/data/curated/interrupciones.json`, una entrada por interrupción. El visor dibuja en rojo los tramos interrumpidos hoy, en el mapa y en el esquema; explica cada interrupción al seleccionar un tramo o un nodo, y añade una nota a los trenes que el horario sigue trayendo.

| Campo | Qué es |
|---|---|
| `id` | Identificador estable: línea, motivo y fecha de inicio. |
| `line_id` | Línea cargada a la que afecta. |
| `from_node`, `to_node` | Nodos extremos, de esa línea y en el orden de su kilometraje. Afecta a todos los tramos que quedan entre ambos. |
| `start_date` | Primer día sin circulación. |
| `expected_end_date`, `expected_end_text` | Previsión de fin que publica la fuente, como fecha o como texto («otoño de 2027»). Opcionales: sin ellos, el visor dice que no hay fecha prevista. |
| `ended_on` | Día en que se reanudó la circulación. Sin él, la interrupción sigue vigente. |
| `reason` | Motivo en una frase neutra. |
| `note` | Opcional: hasta dónde llegan los trenes, qué sigue en servicio, qué se sabe de la reanudación y según quién. |
| `source_ids` | Ids de `sources.json`. La primera es la fuente principal: la que se cita junto a la fecha («… (Adif)»). |
| `checked_on` | Día de la última comprobación en las fuentes. |

Una interrupción está vigente los días `start_date` ≤ día < `ended_on`. Al terminar no se borra: se le pone `ended_on` y queda como registro, y sigue marcando los trenes de las fechas en que estuvo vigente, por ejemplo al simular un cierre en una fecha pasada.

`oniel-data validate` comprueba el fichero sin base de datos y termina con código 1 si algo no encaja: que cada entrada cumple el esquema; que las fechas tienen orden (ni la previsión ni el final son anteriores al inicio, y el final no es posterior a la comprobación); que la línea está cargada; que los dos nodos son de esa línea y van en el orden del kilometraje, y que las fuentes están en `sources.json`, la principal con URL. `oniel-data import interruptions` carga el fichero en la tabla `interruptions` (también lo hace `import all`, después de la red) y, si no encaja con la red cargada, lo rechaza sin tocar lo que había. La API las sirve en `GET /api/interruptions` (con `?date=AAAA-MM-DD`, solo las vigentes ese día) y dentro de `GET /api/network`, que es de donde las lee el visor; la instantánea las lleva en `network.json`, y cada fichero de tramo, las vigentes en el día de referencia.

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

Lo recuerda un flujo de GitHub Actions, `.github/workflows/recordatorio-interrupciones.yml`. Cada lunes a las 07:00 UTC (y a mano, desde la pestaña Actions) lee `interrupciones.json` y, si alguna entrada sin `ended_on` tiene un `checked_on` de más de siete días, abre la incidencia «Revisar las interrupciones del servicio», con la etiqueta `revision-interrupciones` y la lista de entradas pendientes. Mientras haya una abierta con esa etiqueta no abre otra, así que la PR de la revisión debe cerrarla. El flujo solo lee el fichero: no consulta ninguna fuente ni cambia ningún dato. Como se ejecuta una vez por semana, el aviso puede llegar hasta seis días después de cumplirse el plazo.

1. Consultar las fuentes de cada entrada: el estado de la red y los avisos de Adif, la sala de prensa de Renfe y los paneles de salidas y llegadas de las estaciones de los extremos.
2. Resumir lo consultado, con palabras propias, en `backend/data/raw/interrupciones/consultas_<fecha>.json`, y poner al día `sources.json` (`retrieved_on`, `file` y las fuentes nuevas que hagan falta).
3. Editar `interrupciones.json`. `checked_on` cambia siempre. Si la circulación se reanudó, se pone `ended_on`; si cambió la previsión, se corrige; si hay otro corte, se añade una entrada. Si un corte se reabre solo en parte, se acortan sus extremos o se divide en dos entradas. No se infiere nada: lo que la fuente no dice, no se escribe.
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

Cómo se decide qué se muestra:

- El conjunto **vigente** de una fuente es el descargado más recientemente. De los vigentes salen el día de referencia (el laborable con más servicios de sus primeros treinta días) y las cifras de la cobertura.
- El conjunto **activo** de una fuente en un día es el más reciente cuya validez incluye ese día. Los trenes de un tramo, las paradas de una estación, los recuentos y la simulación de un día leen solo los conjuntos activos ese día. `GET /api/coverage` los enumera en `datasets`.
- Se decide por fuente, no por operador: un operador puede publicar ficheros que no se sustituyen entre sí (alta velocidad y cercanías, por ejemplo). Hoy cada operador tiene una sola fuente y da lo mismo.

Cómo se importa:

- `import gtfs` reconoce cada fichero por su SHA-256. Si ya está, rehace sus servicios (las reglas de recorrido pueden haber cambiado) sin duplicar nada; si es nuevo, crea su conjunto y deja los demás como están.
- `import all` importa todos los ficheros de `feeds` y trata la lista como la referencia: reimportar la red borra los pasos por tramo de todos los conjuntos, así que retira de la base el conjunto que ya no esté declarado. El histórico se conserva mientras el fichero siga en `backend/data/raw/` y en `feeds`.
- Cada fichero añade a `import all` el tiempo de leerlo y resolverlo (en local, unos 6 s por fichero de Renfe, medido el 11 de noviembre de 2026; en el plan gratuito de Render, bastante más). Conviene tenerlo en cuenta al acumular histórico.

Para añadir un horario más reciente: guardar el zip en `backend/data/raw/<operador>/` con el día de descarga en el nombre, añadirlo a `feeds` (y poner al día `retrieved_on`, cobertura y notas de su fuente), ejecutar `validate` e `import all` y subir la instantánea. Los recuentos de las pruebas no cambian: usan siempre el fichero del 8 de noviembre de 2026 por su nombre (`backend/tests/conftest.py`).

La instantánea estática lleva solo el estado actual. Para la evolución futura guarda además `frontend/public/data/historico/<conjunto>/segment-counts.json`: los pasos por tramo de cada conjunto en su propio día de referencia. Pesa 2,8 KB por conjunto con los 39 tramos de hoy (medido el 11 de noviembre de 2026), y el visor todavía no lo lee.

## Modelo de datos

Pensado para añadir líneas, operadores y medios de transporte sin rehacer la aplicación.

- `sources`: procedencia, licencia, fecha, cobertura y checksum.
- `operators`: operadores y administradores de infraestructura.
- `lines`: una línea por fila, con `mode` (`ferrocarril` hoy; mañana `metro`, `autobús`…), administrador, ancho, electrificación, orden de presentación (`sort_order`) y geometría completa.
- `nodes` + `line_nodes`: los nodos son independientes de la línea; `line_nodes` da su kilómetro y orden en cada línea, así un nodo puede pertenecer a varias líneas (Madrid-Puerta de Atocha y Córdoba lo hacen). `rank` distingue los nodos principales de los secundarios, que el visor atenúa y oculta en el esquema compacto.
- `segments`: tramos entre nodos consecutivos con geometría, velocidad máxima y habitual, número de vías (`tracks`) y la fuente de su geometría.
- `connections`: hacia dónde continúa la red donde Oniel todavía no tiene datos (se dibujan a trazos).
- `stop_mappings`: cómo se resuelve cada parada de un horario contra la red. La tabla es común a todas las líneas; una parada asignada a un nodo por una línea no la degrada otra que la declare como salida. Las reglas de recorrido (`route_overrides` de cada especificación) no se guardan en la base: solo actúan al importar.
- `datasets`: un conjunto de datos por fichero de horarios importado, con su fuente, su operador, el fichero, su SHA-256, el día de descarga (`retrieved_on`), los días que cubre (`valid_from`, `valid_to`) y cuándo se importó. El id es legible: la fuente y el día de descarga (`renfe-gtfs-av-ld-md-2026-11-08`).
- `services`, `service_dates`, `service_stops`: horarios por tren y día, con el operador y el conjunto de datos del que salen (`dataset_id`, que forma parte de la clave). Cada viaje del GTFS se guarda una sola vez por conjunto aunque recorra varias líneas, y el mismo viaje puede estar en varios conjuntos.
- `service_segment_passes`: el paso de cada tren por cada tramo, precalculado con las reglas de simulación, línea a línea y por conjunto de datos. Un tren que cambia de línea tiene pasos en cada una solo entre las paradas que le corresponden.
- `interruptions`: interrupciones del servicio entre dos nodos de una línea, con sus fechas, el motivo, las fuentes y el día de la última comprobación. Los tramos afectados no se guardan: salen del orden de esos dos nodos en `line_nodes`, de modo que reimportar la red no las deja huérfanas.
- `import_runs`: historial de importaciones con estadísticas.

## Añadir otra línea

1. Descargar la geometría cruda a `backend/data/raw/` con fecha en el nombre y registrar la fuente en `sources.json`. Si la relación OSM trae las dos vías o miembros desordenados, usar `geometry_source.parts` (relación + punto inicial y final de cada parte); si es una relación limpia, basta `file` + `relation_id`.
2. Escribir `backend/data/curated/<línea>.json` con la línea (`sort_order` para el orden en el visor, `tracks` por defecto; `description` en párrafos separados por una línea en blanco, el primero breve porque el visor lo muestra de entrada y pliega el resto, sin repetir longitud, velocidad, ancho ni electrificación, que ya salen en la ficha), sus nodos (coordenadas o kilómetro; `rank: "secundario"` para los menores; `shared: true` para una estación que ya define otra línea), `track_sections` donde cambie el número de vías, las conexiones y la asignación de paradas. Si los puntos kilométricos de la línea no empiezan en cero, `pk_origin_km` lleva el PK de su origen y los `reference_pk_km` de los nodos se escriben tal como los da Adif. En `corridor_filter`, `min_node_stops` y `any_of_stop_ids` evitan que entren trenes de líneas paralelas. Una parada que es nodo de otra línea cargada se asigna como salida con `via` (la línea y el nodo por el que se entra en ella; una lista si el camino cruza más de una). Si un tren recorre esta línea solo en parte y sigue por otra cargada, o la cruza sin parar en ella, declararlo en `route_overrides` (paradas seguidas que lo identifican, tramo de paradas que va por esta línea y, si hace falta, asignaciones propias de esos viajes). Si la línea nueva sustituye a una conexión a trazos de otra especificación, retirarla de allí.
3. Añadir el id de la línea a `line_ids` en `backend/src/oniel/settings.py` (la primera línea de la lista define los nodos compartidos).
4. `uv run oniel-data validate --spec data/curated/<línea>.json` hasta que no haya problemas.
5. `uv run oniel-data import network` e `import gtfs` (sin `--spec` cargan todas las líneas; `import all` hace todo y exporta la instantánea).

El visor dibuja todo lo que devuelve `GET /api/network`: todas las líneas en el mapa y una entrada por línea en la lista de la vista de la red.
