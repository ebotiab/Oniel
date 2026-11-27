# Dos recorridos entre Ourense y Vigo por el nudo de Santiago

Un tren de Ourense a Vigo-Urzáiz puede entrar en Santiago de Compostela, parar y cambiar de sentido, o tomar el enlace de Conxo y continuar hacia Vilagarcía sin entrar en la estación. El comparador debe mostrar ambos caminos. La ficha de un tren debe conservar sus paradas comerciales y explicar con qué evidencia se le atribuye uno de ellos. [Incidencia de implementación #322][tarea].

Preparación del 27/11/2026 sobre [`main` a73d8f4][base]. La [carga de Galicia][galicia-pr] dejó el enlace a trazos. La [incidencia #264][costura] y la [PR #283][costura-pr] hicieron visible la conexión desde ambos extremos. La búsqueda de «Conxo» y «Río Sar» en incidencias, PR y planes encontró esos antecedentes. La futura carga necesita las dos líneas gallegas y un turno exclusivo de datos, incluidos los refrescos GTFS. La planificación mantiene [Ávila–Salamanca #316][avila] antes de [Medina–Salamanca #320][medina]. Conxo queda sin turno asignado.

## Dónde cambia de línea el tren

Adif distingue **dos agujas en A Grandeira**. La línea 082 procedente de Ourense termina en la del PK 85,0 (`B0861`). A partir de ahí los dos recorridos comparten 737 m de la 822 hasta la aguja del PK 376,1 de esa línea (`B0862`). Desde esta última, la 822 sigue a Santiago y la 842 sale hacia Río Sar (`B0902`), donde alcanza la 824 del Eje Atlántico. En sentido Vigo → Ourense se recorren las mismas uniones en orden inverso. El atlas puede reutilizar un eje por corredor en los dos sentidos. La vía de andén y los cruces entre vías paralelas de cada circulación quedan fuera de lo que acreditan estas fuentes. Las numeraciones kilométricas cambian al cambiar de línea. [Tramos en servicio de Adif][tramos] · [topología INSPIRE de Adif][gml] · [Declaración sobre la Red 2026, anexos F y H][dr].

| Lugar, en sentido Ourense → Vigo | Evidencia en la geometría registrada y propuesta para Oniel |
| --- | --- |
| A Grandeira, unión de la vía de Lalín con la de Ourense | Conservar `bif-a-grandeira` y su conexión con la convencional. Está en el km 84,968 del trazado de Oniel. La [conexión a trazos `enlace-conxo`][our] declara este nodo y `to_node_id: bif-rio-sar`. Su dibujo arranca ya en la aguja siguiente. |
| Salida hacia Conxo en la 822 | Crear una bifurcación técnica, por ejemplo `bif-conxo`, dentro de `bif-a-grandeira → santiago`. La [vía OSM 143163375][osm] comparte el nodo **470323194** (−8,5413464°, 42,8548111°) con la vía 822 **208833679**. Su proyección cae en el km **85,702**, a 4 m del eje elegido por Oniel. Los **0,735 km** desde A Grandeira pertenecen a Ourense–Santiago y los usan ambos recorridos. |
| Enlace físico | Cargar una arista entre las agujas **470323194 ↔ 1566507644**. La selección `way_ref: "842"` en el [extracto registrado][raw] da una vía de 32 vértices y **1,011 km**. Los vértices del fichero vienen de Río Sar hacia la 822. Agrupar `enlace-conxo` bajo el Eje en Galicia (`link_of: eje-atlantico`). Importarlo después de sus dos vecinas con ambos nodos compartidos. Retirar el único croquis al cargar la arista. |
| Incorporación en Río Sar | Reutilizar `bif-rio-sar`. La aguja **1566507644** (−8,5533057°, 42,8568421°) pertenece a la 842 y a la vía 824 **264503489**. La relación 1941090 del [Eje][eje] usa la vía paralela. Proyectar la aguja a su eje (4 m), en el km **63,502** desde A Coruña. Esto desplaza el corte unos **79 m hacia Osebe** desde el km 63,423 del nodo actual. Ajustar las dos longitudes adyacentes, Santiago–Río Sar y Río Sar–Osebe. Desde la incorporación hasta Vigo ambos recorridos comparten todo el Eje. |

Las medidas salen de reconstruir cada especificación con `build_network` y proyectar los extremos OSM con `Polyline.project` sobre la polilínea completa. La longitud de la 842 suma las distancias entre vértices con el mismo radio que el importador. Adif da **1.054 m**, vía única, ancho ibérico de 1.668 mm y 25 kV CA. Su eje cartográfico acaba a unos 69 y 163 m de las agujas OSM en los lados de Ourense y Río Sar, respectivamente. Conservar la longitud de catálogo como referencia y usar la geometría OSM para los kilómetros del mapa. OSM etiqueta 50 km/h. La DR acredita ERTMS nivel 1 desde el 30/08/2023. Quedan por verificar una máxima oficial del ramal, el bloqueo, el mando y la fecha de apertura antes de atribuirles valores. [Medición de Oniel][geo] · [ficha geográfica de la 842][ficha] · [DR 2024, §2.6.2, p. 68][ertms].

### Qué distancia debe enseñar el comparador

| Pareja, en ambos sentidos | Por la estación, en la instantánea | Por Conxo, estimación con los cortes anteriores |
| --- | ---: | ---: |
| Ourense ↔ Vilagarcía | 128,1 km | 124,9 km |
| Ourense ↔ Vigo-Urzáiz | **181,6 km** (55 min simulados) | **178,4 km** |
| Madrid-Chamartín ↔ Vigo-Urzáiz | 643,0 km | 639,8 km |

Se comprobó el camino actual con `build_graph` y `find_routes` sobre el [índice publicado][indice]. Por Santiago son 87,841 km hasta la estación y 93,801 km hasta Vigo. Por Conxo serían 85,702 + 1,011 + (155,201 − 63,502) km. Entre agujas, **2,138 + 2,102 km** de entrada y salida por Santiago frente a **1,011 km** de enlace, unos **3,23 km menos** en este modelo. Como contraste independiente, las longitudes de catálogo de Adif dan 2.400 + 2.181 − 1.054 = 3.527 m de diferencia. El eje de Oniel desde Ourense acaba unos 160 m antes del punto de estación. Recalcular con los cortes definitivos y redondear al final. El tiempo simulado se calcula con velocidades de tramo y carece de parada e inversión cronometradas. [Construcción de las dos líneas][datos] · [tramos de Adif][tramos].

## Qué viajes publica Renfe

Se leyeron por separado los tres [GTFS archivados][zips] con `read_feed`, que ordena por `stop_sequence`, aplica calendario y excepciones y agrupa variantes del mismo número que coinciden un día. Se seleccionaron los viajes con Ourense (`22100`) y Vigo-Urzáiz (`08223`) y se buscó además la pareja consecutiva Ourense–Vilagarcía (`23008`) en ambos sentidos en todo el fichero. Los tres ZIP carecen de `shapes.txt` y de horas de paso por las bifurcaciones. Los otros horarios cargados (Ouigo, Iryo y SNCF) carecen de estas paradas. [Lector GTFS][lector] · [registro de ediciones][fuentes].

| Oferta entre Ourense y Vigo-Urzáiz | Viajes por edición Renfe (08 / 12 / 17 de noviembre) | Viernes 11/12/2026, edición del 17 |
| --- | ---: | --- |
| Con parada comercial en Santiago (`31400`) hacia Vigo | **29 / 28 / 28** | **5** · 04475, 04565, 04975, 00622, 37722 |
| Con parada comercial en Santiago hacia Ourense | **18 / 17 / 17** | **5** · 04464, 04494, 04254, 00621, 37621 |
| AVE 04515 hacia Vigo, Ourense y Vilagarcía consecutivas | **6 / 6 / 6** | **1** · Ourense 13:42 → Vilagarcía 14:39 → Vigo 15:16 |
| AVE 04384 hacia Ourense, pareja inversa | **4 / 4 / 4** | **1** · Vigo 17:25 → Vilagarcía 18:00 → Ourense 18:52 |

Cada columna de edición cuenta viajes normalizados con distintas ventanas de calendario. Para localizar los pasos del 11/12, los identificadores de los candidatos son `0451512026-12-09` y `0438412026-11-16`. Entre los que paran en Santiago también aparecen los números 04505 y 04575 en otras fechas. El viernes **20/11/2026**, fecha de #264, se obtienen los mismos cinco más uno por sentido. El sábado **28/11/2026** hay ocho con Santiago y dos candidatos en total. Las ofertas con números diferentes pueden compartir horas. Conservar, por ejemplo, tanto 00621 como 37621. Las paradas «Turístico» con subida y bajada prohibidas siguen sin generar una segunda parada comercial. [Regla de variantes][variantes] · [fichas de Ourense][f-our] y [Vigo-Urzáiz][f-vigo].

**Por Santiago.** El 11/12, el AVE 04565 sale de Ourense a las 18:03, para en Santiago de 18:42 a 18:47 y llega a Vigo a las 19:44. El 04464 sale de Vigo a las 05:50, para en Santiago de 06:46 a 06:51 y llega a Ourense a las 07:25. Renfe anunció expresamente en mayo la parada de ambos números. La parada identifica el recorrido hasta la estación y el esquema de vías explica el cambio de sentido para continuar. [Renfe, cambio de servicio de mayo][renfe-mayo] · [ficha de Santiago][f-san].

**Por Conxo.** 04515 tarda 57 minutos entre la salida de Ourense y la llegada a Vilagarcía. 04384 tarda 52 minutos en sentido inverso. En mayo, *La Voz de Galicia* identificó expresamente el baipás para el AVE de las 17:25 desde Vigo. Para el de las 11:17 desde Madrid, el artículo enumera sus paradas. Ambas horas y las paradas coinciden con las de estos dos servicios del fichero del 17/11. Es un antecedente de itinerario para 04384 y una coincidencia comercial para 04515. **Falta una fuente de Adif o Renfe que vincule cada número, sentido y periodo del horario con la 842**. Hasta conseguirla, conservar la atribución como inferencia y mantener visible su grado de certeza. Un tren puede atravesar una estación sin parada comercial. [Información del 20/05/2026][prensa] · [horario de Renfe][gtfs].

## Cómo asignar los pasos

En las dos especificaciones gallegas, `ourense-vilagarcia-sin-santiago` reconoce `[22100, 23008]` y su inversa. Hoy saca el tren en A Grandeira y lo recupera en Río Sar, con un salto en línea recta en el reparto del tiempo. En los tres ficheros, los únicos viajes que casan siguen la secuencia completa **Chamartín – Zamora – Ourense – Vilagarcía – Pontevedra – Vigo-Urzáiz** (`17000, 30200, 22100, 23008, 23004, 08223`) o su inversa. Usar esta secuencia comprobada para la asignación específica y revisar un patrón nuevo al refrescar el horario. Un viaje con Santiago conserva la asignación por defecto. [Regla de Ourense][our] · [regla del Eje][eje] · [selección y resolución de itinerarios][reglas].

| Especificación | Asignación del patrón directo una vez respaldado |
| --- | --- |
| Enlace | Resolver el intervalo entre `22100` y `23008` en ambos sentidos. Ourense sale por la aguja nueva con `via` por Ourense–Santiago y Vilagarcía por Río Sar con `via` por el Eje. Son dos paradas exteriores. El filtro ordinario exige una parada en un nodo del enlace, condición que ningún viaje cumple. La regla específica incorpora el patrón acreditado. El tren genera un paso estimado por la arista y cero paradas en las agujas. |
| Ourense–Santiago y Eje Atlántico | Para `23008/23004/08223`, la primera sale por la aguja nueva, recorre la 842 hasta Río Sar y sigue por el Eje. Para `22100/30200/17000`, el Eje recorre el enlace en sentido contrario y continúa por Ourense–Santiago, Olmedo y Valladolid hasta donde corresponda. Cada salto de `via` comparte el nodo de salida con la línea siguiente. |
| Olmedo–Zamora–Ourense y Madrid–Segovia–Valladolid | Las asignaciones generales de las tres paradas costeras pasan de `lav-ourense-santiago` a `eje-atlantico` en `santiago`. Olmedo las alcanza desde `ourense`. Valladolid sale por `bif-medina` y antepone la línea de Olmedo. Solo para el patrón directo, intercalar la 842 entre la nueva aguja y Río Sar en ambas cadenas. Mantener las salidas generales para quienes paran en Santiago y para A Coruña. [Olmedo][olmedo] · [Valladolid][valladolid]. |

En **ambas** líneas lejanas, 04515 y 04384 ya encajan con `madrid-zamora-sin-parada`. El importador aplica la primera regla coincidente. Si se añade una más específica, situarla antes y conservar el límite `from_stop_id: 17000` y su inversión, además de la selección y los pasos entre Chamartín, Medina, Zamora y Ourense. Probar también `madrid-ourense-sin-parada` con un tren que pase por Santiago. Dejar intactos los regionales de la vía de Lalín, del Padrón antiguo y de Vigo-Guixar. [Orden de las reglas y medida de los `via`][reglas].

## Comprobaciones de aceptación

Se ensayó el grafo en memoria con cinco nodos (Ourense, las dos agujas, Santiago y Vigo), las longitudes medidas y los lados físicos de las agujas. Con el triángulo ordinario, incluso con `max_ratio=100`, solo apareció Conxo y su cierre dejó la pareja sin camino. Al orientar el enlace hacia la salida a Vigo con `link_towards`, aparecieron las dos rutas con 100 y solo Conxo con el valor ordinario 2. En la red completa el vecino inmediato de Río Sar hacia Vigo es `osebe`. Ensayar esa orientación con controles de giro en **ambos** extremos. [Grafo del servidor][grafo] · [comparador del visor][comparador].

1. **Giros en las agujas y en la estación.** Admitir Ourense ↔ 842 ↔ Osebe y la continuidad de cada línea hacia Santiago. Impedir pasar directamente del brazo de Santiago a la 842 en cualquiera de las dos agujas. En Santiago sí se puede entrar por la 822 y salir por la 824 tras invertir. El triángulo ordinario de `link_of` prohíbe encadenar dos de sus lados incluso en su vértice de estación. Además, los rumbos actuales a 500 m se miden en plena curva. En la aguja oriental, las direcciones hacia Ourense y hacia Santiago forman 123° y en la occidental, las de Santiago y Osebe, 131°. Ambas quedan fuera de los umbrales de continuidad. A 100 m los tres ángulos entre brazos en la oriental son 169° (Ourense/Santiago), 175° (Ourense/enlace) y 6° (Santiago/enlace). En la occidental son 163° (Santiago/Osebe), 9° (Santiago/enlace) y 172° (Osebe/enlace). Resolver localmente estos movimientos acreditados y probar los dos sentidos. Conservar las restricciones y pruebas de los demás enlaces. [Giros][giros] · [triángulos del grafo][grafo].
2. **Dos rutas en la consulta ordinaria.** Con la red disponible y sin escenario, pedir `GET /api/routes?from=ourense&to=vigo-urzaiz&date=2026-12-11` y la inversa. Abrir `/recorridos/ourense/vigo-urzaiz` y la inversa con `ONIEL_E2E_STATIC=1`. Los dos motores deben devolver primero el camino de unos 178,4 km por la 842 y después el de 181,6 km con Santiago. Comparar `node_ids`, `segment_ids`, orden, kilómetros y minutos calculados. El filtro por defecto `max_ratio=2` compara solo las partes distintas, aquí **4,240 / 1,011 ≈ 4,2**. Incluir en ambos motores el itinerario comercial por Santiago en la consulta normal. Subir el límite a 100 sirve para diagnosticar el filtro, una vez resueltos los giros. Repetir con cierre de la 842 y con cierre del brazo aguja–Santiago, uno por vez. En la API, usar el parámetro `scenario=c~<id-del-tramo>` con el ID devuelto en `segment_ids`. En cada caso queda transitable el otro camino. Controlar Ourense ↔ Santiago, Santiago ↔ Vigo y Madrid ↔ Vigo. [API de rutas][api] · [comparador estático][comparador] · [casos de paridad][paridad].
3. **Los mismos servicios en horarios y comparador.** Para el 11/12, cruzar `/api/nodes/{id}/services?date=2026-12-11` en origen y destino por `service_id`, sentido y permisos de subida/bajada. Comparar con las paradas de la instantánea y con `/api/segments/{id}/services?date=2026-12-11` y los JSON de tramos. En cada sentido debe haber seis directos y cinco en los dos brazos de Santiago. Si se confirma la asignación propuesta, solo 04515 en la ida y 04384 en la vuelta han de figurar en la ficha de la 842, una vez, con paso estimado dentro de sus respectivos intervalos **13:42–14:39** y **18:00–18:52**. Distinguir cada recorrido por sus tramos exclusivos, la 842 en uno y los dos brazos de Santiago en el otro, aunque el visor agrupe el enlace bajo el Eje. Los dos conjuntos de identificadores han de ser disjuntos y su unión ha de dar los seis. Mientras un itinerario esté pendiente, identificarlo como tal. [Prueba de directos][directos] · [ficha actual Santiago–Río Sar][f-sar].
4. **Contabilidad antes y después.** El 11/12 las fichas dan **45** pasos entre Coto da Torre y A Grandeira, **43** entre A Grandeira y Santiago, **53** entre Santiago y Río Sar y **55** entre Río Sar y Osebe. Con los dos candidatos confirmados, el nuevo tramo compartido A Grandeira–aguja recibe 45, el brazo aguja–Santiago conserva 43 y la 842 recibe 2. Los tramos del Eje conservan 53 y 55 en sus respectivas fichas. Comprobar por edición y día la unicidad de viaje y de pareja servicio/tramo, horas comerciales y continuidad del reparto en ambos límites. La suma de los tramos partidos recupera los kilómetros de cada línea madre. La red solo gana la longitud propia de la 842, una arista de enlace y el tramo adicional producido al partir la 822. [Ficha actual de Ourense–Santiago][f-linea] · [ficha actual del Eje][f-eje].
5. **Entrega posterior.** Registrar cada fuente nueva con licencia, cobertura y fecha, conservar originales fechados y actualizar la cobertura de `osm-vias-santiago-sur`. Validar especificaciones, atributos, giros, horarios y alternativas de cierre. Comprobar que mapa y esquema enlazan las dos fichas técnicas y no conservan otro trazo de Conxo. Probar la importación con los tres GTFS de Renfe, las [regresiones de Galicia][pruebas] y la paridad Python/TypeScript, Playwright estático y con API local. Actualizar inventario, recuentos e histórico y regenerar la instantánea una vez en el turno de datos. [Documentación de datos][doc-datos].

## Fuentes y condiciones de uso

Consulta del 27/11/2026. Las fechas de archivo distinguen las ediciones utilizadas para las medidas.

| Fuente | Uso y licencia |
| --- | --- |
| Colaboradores de OpenStreetMap. [Extracto del 18/11][raw], relaciones 4777980 y 1941090 y `osm-instalaciones-galicia` en el [registro][fuentes] | Geometría, etiquetas y posiciones de las vías y nodos. [ODbL 1.0 con atribución][odbl]. La tabla de PK usada en la carga anterior figura como `wikipedia-lav-ourense-santiago` (CC BY-SA 4.0). |
| Adif. [Tramos en servicio][capa] y [WFS INSPIRE, edición 2026/01, copia del 07/08][gml] | Contraste de topología, kilometraje de catálogo y tipo de vía. Atribución «© Administrador de infraestructuras ferroviarias». La fila 068420010 identifica la 842 y el WFS enlaza sus extremos B0862 y B0902. [Condiciones de la capa][capa] · [metadato INSPIRE][meta]. |
| Adif. [DR 2026 de 27/03][dr] y [DR 2024, §2.6.2][ertms] | Verificación documental de extremos, ancho, alimentación y ERTMS. Consulta pública, © Adif. Para publicar geometría se propone el extracto OSM registrado. |
| Renfe Viajeros. [GTFS AV/LD/MD][gtfs] y [nota de mayo de 2026][renfe-mayo] | Los [ZIP del 08, 12 y 17/11][zips] tienen licencia CC BY 4.0. La nota es una referencia editorial © Renfe sobre dos paradas comerciales. |
| *La Voz de Galicia*. [Información del 20/05/2026][prensa] | Referencia periodística, © del editor. Aporta el antecedente de la salida de Vigo de las 17:25. |

[tarea]: https://github.com/ebotiab/Oniel/issues/322
[base]: https://github.com/ebotiab/Oniel/commit/a73d8f48c0086fccbf69412b961f0292a6e59edb
[galicia-pr]: https://github.com/ebotiab/Oniel/pull/225
[costura]: https://github.com/ebotiab/Oniel/issues/264
[costura-pr]: https://github.com/ebotiab/Oniel/pull/283
[avila]: https://github.com/ebotiab/Oniel/issues/316
[medina]: https://github.com/ebotiab/Oniel/issues/320
[doc-datos]: ../datos.md
[datos]: ../datos.md#cómo-se-construyeron-las-líneas-de-alta-velocidad-ourensesantiago-y-a-coruñasantiagovigo
[our]: ../../backend/data/curated/lav-ourense-santiago.json
[eje]: ../../backend/data/curated/eje-atlantico.json
[olmedo]: ../../backend/data/curated/lav-olmedo-ourense.json
[valladolid]: ../../backend/data/curated/lav-madrid-valladolid.json
[osm]: https://www.openstreetmap.org/way/143163375
[raw]: ../../backend/data/raw/osm/vias_santiago_sur_2026-11-18.json
[geo]: ../../backend/src/oniel/geo.py
[fuentes]: ../../backend/data/curated/sources.json
[indice]: ../../frontend/public/data/index.json
[zips]: ../../backend/data/raw/renfe
[lector]: ../../backend/src/oniel/gtfs/reader.py
[variantes]: ../../backend/src/oniel/gtfs/variants.py
[reglas]: ../../backend/src/oniel/gtfs/trips.py
[giros]: ../../backend/src/oniel/routing/turns.py
[grafo]: ../../backend/src/oniel/routing/graph.py
[api]: ../../backend/src/oniel/api/routers/routes.py
[comparador]: ../../frontend/src/app/recorridos.ts
[paridad]: ../../frontend/e2e/rutas.spec.ts
[directos]: ../../frontend/e2e/recorridos.spec.ts
[pruebas]: ../../backend/tests/test_galicia.py
[f-our]: ../../frontend/public/data/nodes/ourense.json
[f-vigo]: ../../frontend/public/data/nodes/vigo-urzaiz.json
[f-san]: ../../frontend/public/data/nodes/santiago.json
[f-sar]: ../../frontend/public/data/segments/eje-atlantico--santiago--bif-rio-sar.json
[f-linea]: ../../frontend/public/data/lines/lav-ourense-santiago.json
[f-eje]: ../../frontend/public/data/lines/eje-atlantico.json
[capa]: https://www.arcgis.com/home/item.html?id=4ec7c0fb3cab42b0b488d65e65eeb7aa
[tramos]: https://services7.arcgis.com/XTupIrLX53AjaJqO/arcgis/rest/services/Tramos_en_servicio_Adif_p%C3%BAblico/FeatureServer/0/query?where=CODTRAMO+IN+%28%27068420010%27%2C%27068220114%27%2C%27068220116%27%2C%27068240053%27%2C%27068240044%27%2C%27160820120%27%29&outFields=CODTRAMO%2CCOD_LINEA%2CDEPORIGEN%2CDEPDESTINO%2CPKI%2CPKD%2CLONGITUD%2CCOD_TIPO_V&returnGeometry=false&f=pjson
[ficha]: https://services7.arcgis.com/XTupIrLX53AjaJqO/arcgis/rest/services/Tramos_en_servicio_Adif_p%C3%BAblico/FeatureServer/0/5555?f=pjson
[gml]: https://github.com/ArturoVazquez/atlas-archivo/blob/4677145ef514b0030de5adce3b5fce5501a44b2a/fuentes/adif/2026/2026-08-07_adif_red-ferroviaria-wfs-inspire.zip
[meta]: https://www.idee.es/csw-codsi-idee/srv/api/records/62c487b1-6816-4594-a800-218abe896994/formatters/xml
[dr]: https://www.adif.es/documents/20124/51645141/20260327_01_DR%2BADIF_V1_LIBRO_2026.pdf/ad3f9339-e36e-8ad1-a931-22cd1a34e8fa?t=1774634014267
[ertms]: https://www.adif.es/documents/20124/26593593/20240205_01_DR_Adif_Libro_2024_V1.pdf/36f0b3eb-65ad-3188-d43c-1456c7a87ddb
[renfe-mayo]: https://grupo.renfe.com/es/es/sala-de-prensa/noticias/2026/05/renfe-mejora--conexion-matinal-entre-galicia-castilla-leon-madrid
[prensa]: https://www.lavozdegalicia.es/noticia/vigo/vigo/2026/05/19/viajes-ave-vigo-madrid-tardan-partir-hoy-4-horas/00031779211909172968166.htm
[gtfs]: https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia
[odbl]: https://www.openstreetmap.org/copyright
