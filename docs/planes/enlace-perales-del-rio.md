# El paso de los AVE Barcelona–Andalucía por Perales del Río

El horario ofrece dos maneras de viajar sin transbordo entre Barcelona-Sants y Sevilla-Santa Justa. Hay AVE que evitan Madrid-Puerta de Atocha y trenes que entran en la estación y vuelven a salir. Oniel reconoce ambos en los horarios. Al grafo le falta la vía que une la alta velocidad de Barcelona y la de Sevilla por Perales del Río. Incorporarla acortaría el recorrido del comparador unos **20,1 km** y permitiría distinguirlo del recorrido con parada en Atocha. [Incidencia de implementación #329][incidencia]

Preparación del 27/11/2026 sobre [`main` en bc8c4414][base]. La búsqueda de Perales, Vallecas y Los Gavilanes en planes, incidencias y PR encontró las reglas de asignación y la conexión dibujada a trazos desde ambos extremos. La hoja de ruta aún recogía el paso por Madrid como pendiente de incidencia. Esta es su primera preparación específica. [Reglas de Madrid–Sevilla][reglas-sur] · [conexiones a trazos][costuras] · [hoja de ruta][hoja]

## Dos trenes entre las mismas estaciones

Se abrió el visor de `bc8c4414` con `VITE_DATA_MODE=estatico npm --prefix frontend run dev`, sin escenario, y se cruzaron las paradas de origen y destino con los pasos por tramo de su instantánea. El día de los horarios es el **viernes 11/12/2026**. En Barcelona → Sevilla se ven cinco trenes directos. El recorrido más corto pasa por Atocha y mide **1.090,3 km** con **3 h 58 min** teóricos sin paradas. Se le asignan el Ouigo 6410 y los Iryo 06012 y 06014. Los AVE 03940 y 03942 quedan fuera de los tres recorridos visibles. En la inversa también hay cinco, tres por Atocha y dos fuera (03943 y 03941). La longitud se calcula por los baipases de Zaragoza y Lleida y el panel avisa de la diferencia si se entra en sus estaciones. El aviso de interrupción La Sagra–Córdoba acompaña a la consulta. Las cifras describen la oferta programada. [Abrir la ida][ida] · [abrir la vuelta][vuelta] · [fecha de la instantánea][cobertura] · [parte de Adif archivado][parte]

| Control del 11/12 | Paradas publicadas que distinguen el paso por Madrid | Qué se ve en las fichas |
| --- | --- | --- |
| AVE 03940, Barcelona 08:30 → Sevilla 14:47 | Sale de Zaragoza-Delicias a las 10:22 y la siguiente parada es Ciudad Real a las 12:36. Después para en Puertollano y Córdoba. | Aparece en Guadalajara-Yebes–Vallecas y Los Gavilanes–Torrejón de Velasco. Su paso es estimado en ambos. Está ausente de la ficha de Atocha y de sus dos tramos de acceso. |
| Ouigo 6410, Barcelona 07:35 → Sevilla 14:21 | Sale de Zaragoza a las 09:10, llega a Madrid-Puerta de Atocha a las 11:05, sale a las 11:40 y llega a Córdoba a las 13:25. | La ficha de Atocha muestra el 6410 a las 11:40. Figura en Vallecas–Atocha (11:00–11:05) y Atocha–Los Gavilanes (11:40–11:44). La consulta Zaragoza → Atocha permite reproducir por separado su entrada, con 306,5 km de recorrido. |

La consulta Barcelona → Málaga ofrece un segundo control del mismo paso por Madrid. Hay dos trenes directos. El Iryo 06020 aparece en el recorrido de 1.132,8 km por Atocha, donde tiene parada de 14:42 a 15:05. El AVE 03990, que sale de Barcelona a las 08:30, queda fuera de los recorridos visibles. [Barcelona–Málaga][malaga] · [horarios y procedencia][fuentes]

Para repetirlo, abrir las consultas y buscar los números en la ficha de la estación y en «Trenes que lo recorren». El detalle de la marca «estimado» explica el cálculo. Entre las dos bifurcaciones el mapa dibuja un trazo discontinuo, `enlace-vallecas-perales-del-rio`. Las dos fichas de bifurcación lo anuncian como «no cargada todavía», cada una con el destino del otro lado. Son puntos donde se juntan las vías, sin paradas de viajeros. [Consulta de control][control] · [Atocha][atocha] · [Vallecas][vallecas] · [Los Gavilanes][gavilanes] · [tramo del lado de Barcelona][ficha-este] · [tramo del lado de Sevilla][ficha-sur]

**Dónde interviene la línea recta**

- En Madrid–Sevilla, las reglas `barcelona-ciudad-real-sin-parar-en-madrid` y `barcelona-cordoba-sin-parar-en-madrid` sitúan la salida en Los Gavilanes. Su `via` empieza en Vallecas. Para el 03940, la ficha reparte el tiempo Zaragoza–Ciudad Real usando 294 km de vía hasta Vallecas, **5,145 km en línea recta** entre los nodos (se muestran como 5 km) y 157 km de vía desde Los Gavilanes. [Reglas de Sevilla][sev] · [distancia con `via`][via]
- En Madrid–Barcelona, las salidas andaluzas generales por Vallecas carecen de `via`. Se usa la recta **desde Vallecas hasta la parada exterior**, en este caso Ciudad Real. El efecto se aprecia al seguir el 03940 de una ficha a otra. Termina el tramo de Guadalajara en Vallecas a las 11:50 y entra en Los Gavilanes a las 11:49, según estimaciones independientes. [Asignaciones de Barcelona][bcn] · [cálculo del paso][pasos] · [ficha del tramo este][pasos-este] y [del tramo sur][pasos-sur]

Los 1.090,3 km del comparador proceden de la suma de los tramos cargados por Atocha. La conexión discontinua sirve de referencia en el mapa. [Índice del grafo][indice]

## Qué acredita cada fuente

Fuentes consultadas el 27/11/2026. Las ediciones del horario se leyeron por separado, en orden de parada, con calendario y excepciones.

| Fuente | Alcance de la evidencia |
| --- | --- |
| Adif Alta Velocidad, reglamento publicado en el BOE en 2025, y capa de tramos en servicio de Adif | La **línea 068** enlaza Vallecas AV, aguja del PK 12,300 de la 050 (`B6001`), y Los Gavilanes, aguja del PK 13,400 de la 010 (`B3710`). El registro `120680010` consigna 5.552 m, vía doble y estado en servicio. Los PK de sus nombres pertenecen a líneas distintas. [Reglamento de Adif AV][boe] · [ficha cartográfica de Adif][adif-tramo] |
| Adif, *Cuadro de velocidades máximas*, grupo 2, edición de 11/10/2016, PDF p. 19 | Distingue **5,6 km** de Vallecas a Los Gavilanes (sentido par) y **4,9 km** a la inversa (impar). Recoge 160 km/h en ambos. Es una referencia fechada para contrastar las vías y su sentido. Para publicar límites actuales, comprobar la edición vigente. [Cuadro de la 068][cvm] |
| Ministerio de Fomento, 20/04/2016, y Renfe, 29/04/2026 | Fomento identifica el baipás de Atocha sur como camino de la relación directa sur–noreste. Renfe documenta los AVE Sevilla–Zaragoza–Barcelona sin escala en Madrid y la oferta directa de Málaga y Granada. Para Granada especifica que se evita el transbordo. El comunicado da frecuencias y fechas de reposición, sin identificar una vía para cada número de tren en diciembre. [Itinerario descrito por Fomento][fomento] · [servicios anunciados por Renfe][renfe] |
| Horarios de Renfe Viajeros (CC BY 4.0), Ouigo y la compilación no oficial de Iryo | Los ficheros GTFS acreditan paradas, horas y días de servicio. Los ZIP de Renfe carecen de `shapes.txt`. Una omisión de Atocha en `stop_times.txt` solo establece la ausencia de parada comercial. Para asignar un número o patrón a la 068, contrastarlo con un itinerario, marcha o documento de explotación de Adif o Renfe que cubra su sentido y periodo. [Catálogo de Renfe][catalogo] · [ZIP de Renfe][zips] · [ZIP de Ouigo][ouigo] · [procedencia y licencias][fuentes] |
| © colaboradores de OpenStreetMap, ODbL 1.0 | La relación ferroviaria **17684502** (v1) contiene las dos vías con `ref=068`. Sus agujas comparten nodos con las vías de la 050 y la 010. Las etiquetas dan 1.435 mm, 25 kV y 160 km/h. Es geometría de infraestructura. El uso de una vía concreta por un tren sigue dependiendo de la documentación de circulación. [Relación 068][osm] · [vías y vértices][osm-datos] |

## Medición entre las agujas

Se reutilizan `bif-vallecas-av` de `lav-madrid-barcelona`, `bif-los-gavilanes` de `lav-madrid-sevilla`, los tramos exteriores hacia Guadalajara y Torrejón de Velasco, y los dos accesos a `madrid-puerta-de-atocha`. En el índice actual, Vallecas está en el km 12,011 de Oniel y Los Gavilanes en el km 13,445. Cada bifurcación reúne dos agujas físicas a distinta altura de la línea. La orientación de las dos cadenas OSM concuerda con los dos desarrollos del cuadro de Adif. [Especificación de Barcelona][bcn] · [especificación de Sevilla][sev] · [cuadro por sentido][cvm]

| Movimiento | Agujas OSM, en orden de marcha | Vías OSM encadenadas, en ese orden | Longitud de vía | Km proyectado en 050 / 010 |
| --- | --- | --- | ---: | ---: |
| Barcelona → Andalucía, Vallecas → Los Gavilanes | `1112971596` → `365110834` | `28455394`, `28455391`, `28455392`, `288041026`, `32473725`, `28455380` | **5,420 km** | 12,271 / 13,261 |
| Andalucía → Barcelona, Los Gavilanes → Vallecas | `1097807822` → `1112971422` | `32473752`, `28455432`, `96061559`, `96061558` | **4,737 km** | 11,717 / 13,143 |

Para repetir la medida, descargar la relación completa, separar las dos cadenas de vías `068` por sus nodos comunes y sumar `haversine_km` entre vértices consecutivos (radio 6.371,0088 km). Reconstruir las dos líneas con `build_network` y proyectar cada aguja con `line.polyline.project`. Las cuatro distan menos de 6 m de sus ejes. La selección por `ref=068` deja fuera las vías próximas de la conexión con Levante (040). En la capa de Adif, pedir la geometría de la 068 en coordenadas geográficas (`outSR=4326`). Su eje único mide 5,469 km con el mismo método. Los metros de catálogo y los recorridos por cada vía tienen extremos y precisión distintos. [Extracto OSM][osm-datos] · [empalmes con la 050 y la 010][osm-nudo] · [eje de Adif en coordenadas geográficas][adif-eje] · [medición de Oniel][geo]

Con dos puntos exteriores comunes se ve qué ahorra el enlace. Entre Guadalajara-Yebes (km 64,371) y la bifurcación Torrejón de Velasco (km 28,705), el camino por Atocha suma **93,076 km** en los dos sentidos. Por Perales, la ida mide `(64,371 − 12,271) + 5,420 + (28,705 − 13,261) ≈ 72,965 km` y la vuelta, `(28,705 − 13,143) + 4,737 + (64,371 − 11,717) ≈ 72,953 km`. Se ahorran respectivamente **20,111 y 20,123 km**, redondeando tras la suma. La ubicación diferente de las agujas explica que las dos vías difieran casi 700 m y los recorridos entre los puntos comunes, unos 11 m. [Tramos del índice][indice]

## Propuesta de carga

**Geometría.** Sustituir el trazo por un enlace seleccionable, con `link_of` apuntando a Madrid–Barcelona. Para el modelo bidireccional de Oniel se propone la cadena de **5,420 km** como eje representativo. Conservar los identificadores de bifurcación, ajustar sus posiciones sobre las líneas madre a las agujas de ese eje y mantener el PK de referencia por separado. Así se contabiliza una sola vez cada metro de acceso. [Procedimiento de carga][carga] · [precedente de Monforte del Cid][monforte]

**Asignación.** Los candidatos llevan seguidas Zaragoza (`04040`) y Ciudad Real (`37200`), o Zaragoza y Córdoba (`50500`), en ambos órdenes. Para cada patrón respaldado, asociar la fecha y el itinerario que lo acreditan. En el filtro del enlace, exigir esas secuencias y excluir los trenes con parada en Madrid-Puerta de Atocha (`60000`) o con itinerario por València. Revisar cualquier patrón nuevo al refrescar los horarios. [Selección de viajes][via]

| Dónde se calcula el paso | Camino que debe usar el reparto de tiempos |
| --- | --- |
| En la 068 | Las dos paradas del horario quedan fuera del enlace. Medir con `via` desde Vallecas por la 050 hasta Zaragoza y desde Los Gavilanes por la 010 hasta Ciudad Real o Córdoba. Estimar el paso por la 068 entre ambas paradas. |
| En Madrid–Sevilla | En las dos reglas de los AVE sin parada en Madrid, anteponer la 068 desde Los Gavilanes al actual `via` que sigue desde Vallecas por la 050. |
| En Madrid–Barcelona | Para los directos acreditados, completar el `via` desde Vallecas por la 068 y la 010 hasta la parada, prolongándolo por las líneas cargadas cuando corresponda. Conservar la regla `barcelona-andalucia-con-parada-en-madrid` (Zaragoza–Atocha–Córdoba y viceversa) y cubrir los trenes con más paradas. `barcelona-cordoba-por-valencia` conserva su salida por Camp de Tarragona. |

**El recorrido con parada en Atocha.** En una prueba en memoria sobre el índice se movieron los cortes a las agujas propuestas y se añadió la arista de 5,420 km. Con `link_of` solo, la regla del triángulo impide pasar de un acceso al otro en Atocha. Con `link_towards: guadalajara-yebes` y los giros físicos en las dos bifurcaciones, se recupera el camino por Atocha con `max_ratio=100`. El valor normal, 2, sigue descartándolo porque compara las partes distintas, 25,532 km por Atocha frente a 5,420 por Perales. Resolver esta excepción para el recorrido comercial por la terminal en los dos motores. [Grafo del servidor][grafo] · [grafo del visor][grafo-visor]

## Pruebas de aceptación

1. **Giros y kilómetros.** Verificar en ambos sentidos Guadalajara ↔ Vallecas ↔ Los Gavilanes ↔ Torrejón, además de la continuidad de cada línea hacia Atocha. Rechazar el giro desde el enlace hacia Atocha en cada bifurcación. Con la misma importación y sin escenario, pedir `GET /api/routes?from=barcelona-sants&to=sevilla-santa-justa&date=2026-12-11` y su inversa. Comparar con `findRoutes` sobre el índice exportado. Deben coincidir las secuencias de `node_ids`, `segment_ids` y `line_ids`, la suma de tramos y `length_km`. En el comparador estático, con parámetros normales, deben verse **unos 1.070,2 km por Perales y 1.090,3 km por Atocha** si el resto del recorrido se mide igual. Fijar los valores de la prueba con los cortes definitivos. [API de rutas][api] · [prueba de paridad Python/TypeScript][paridad]
2. **Un paso por el enlace o una parada en Atocha.** Con itinerario acreditado, el AVE 03940 tendrá un solo paso estimado por la 068 entre Zaragoza (10:22) y Ciudad Real (12:36), y el 03943 entre Ciudad Real (10:29) y Zaragoza (12:46). Ambos tendrán cero pasos por los dos accesos a Atocha. Repetir con la variante del 03940 del 13/12 (Zaragoza 10:22 → Córdoba 13:29). Los Ouigo 6410 y 6415 y los Iryo que paran en Atocha conservarán las horas publicadas, ambos accesos y cero pasos por la 068. Incluir el Iryo 06011, que entre Córdoba y Atocha para también en Puertollano y Ciudad Real. Comprobar las asignaciones por número, pues una regla de recorrido puede incorporar un viaje excluido por el filtro. [Reglas actuales][via] · [horarios archivados][fuentes]
3. **Cada viaje cuenta una vez.** Los tres ZIP de Renfe (08, 12 y 17/11) contienen, cada uno, 16 variantes candidatas de ocho números de AVE, ocho variantes por pareja de paradas. El 11/12 hay ocho números activos para Sevilla, Málaga y Granada, cuatro por sentido. Para Barcelona–Sevilla, con los dos AVE acreditados por sentido, exigir **2 por Perales + 3 por Atocha = 5** en la ida y en la vuelta. Comparar las identidades de los cinco antes y después. Ninguna debe aparecer en ambos recorridos. Exigir un viaje por operador, número y día del conjunto activo y un paso por `(dataset_id, service_id, segment_id)`. El 03940 hacia Sevilla y el 03990 hacia Málaga comparten hora de salida y son dos viajes distintos. [Lector de horarios][lector] · [pruebas del comparador][pruebas-visor]
4. **Fichas y cierres.** Con la fecha de referencia, comparar `/api/nodes/{id}/services` y `/api/segments/{id}/services` con las fichas estáticas. Deben coincidir identificadores, horas y tipos de paso. En las agujas, exigir un tramo seleccionable y cero paradas comerciales. En los tramos, exigir kilómetros de vía y pasos ordenados entre ambas líneas. Cerrar primero la 068 y, en otro escenario, uno de los accesos a Atocha. El grafo permite el otro camino en cada caso y el visor identifica el recorrido cerrado. Conservar por separado el aviso de interrupción del corredor. [Fichas de referencia del tramo este][pasos-este] y [del tramo sur][pasos-sur]
5. **Entrega de la futura carga.** Registrar las fuentes con licencia, fecha y cobertura, guardar sus originales fechados y ejecutar `oniel-data validate`. Sobre la misma importación, regenerar la instantánea y revisar los cambios en las fichas, los recuentos y la documentación. Pasar las pruebas de reglas, la comparativa compartida y Playwright en modo estático y con API local. [Procedimiento de Oniel][carga]

**Pendiente de confirmar para la implementación.** Vincular los servicios y periodos concretos a la 068 con documentación de circulación, contrastar los límites actuales y validar los cortes y giros al importar. Hasta entonces los ocho números del horario son candidatos. El registro de viajes por la 068 dependerá del respaldo que se obtenga para cada patrón. [Seguimiento de la carga][incidencia]

[incidencia]: https://github.com/ebotiab/Oniel/issues/329
[base]: https://github.com/ebotiab/Oniel/tree/bc8c4414d0c863cc5860c1abaa73f71ec1217201
[reglas-sur]: https://github.com/ebotiab/Oniel/pull/153
[costuras]: https://github.com/ebotiab/Oniel/pull/283
[hoja]: ../hoja-de-ruta.md
[ida]: https://oniel.vercel.app/recorridos/barcelona-sants/sevilla-santa-justa
[vuelta]: https://oniel.vercel.app/recorridos/sevilla-santa-justa/barcelona-sants
[malaga]: https://oniel.vercel.app/recorridos/barcelona-sants/malaga-maria-zambrano
[control]: https://oniel.vercel.app/recorridos/zaragoza-delicias/madrid-puerta-de-atocha
[atocha]: https://oniel.vercel.app/nodo/madrid-puerta-de-atocha
[vallecas]: https://oniel.vercel.app/nodo/bif-vallecas-av
[gavilanes]: https://oniel.vercel.app/nodo/bif-los-gavilanes
[ficha-este]: https://oniel.vercel.app/tramo/lav-madrid-barcelona:bif-vallecas-av:guadalajara-yebes
[ficha-sur]: https://oniel.vercel.app/tramo/lav-madrid-sevilla:bif-los-gavilanes:bif-torrejon-de-velasco
[cobertura]: ../../frontend/public/data/coverage.json
[parte]: ../../backend/data/raw/interrupciones/consultas_2026-11-25.json
[bcn]: ../../backend/data/curated/lav-madrid-barcelona.json
[sev]: ../../backend/data/curated/lav-madrid-sevilla.json
[via]: ../../backend/src/oniel/gtfs/trips.py
[pasos]: ../../backend/src/oniel/sim/passes.py
[indice]: ../../frontend/public/data/index.json
[boe]: https://www.boe.es/buscar/doc.php?id=BOE-A-2025-23895
[adif-tramo]: https://services7.arcgis.com/XTupIrLX53AjaJqO/arcgis/rest/services/Tramos_en_servicio_Adif_p%C3%BAblico/FeatureServer/0/5697?f=pjson
[adif-eje]: https://services7.arcgis.com/XTupIrLX53AjaJqO/arcgis/rest/services/Tramos_en_servicio_Adif_p%C3%BAblico/FeatureServer/0/query?where=CODTRAMO%3D%27120680010%27&outFields=CODTRAMO%2CLONGITUD&returnGeometry=true&outSR=4326&f=pjson
[cvm]: https://contractaciopublica.cat/portal-api/descarrega-document-antic/80661536/c77559684778ef8708621614aa8abab5#page=19
[fomento]: https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/mfom/Paginas/2016/200416-altavelocidad.aspx
[renfe]: https://grupo.renfe.com/es/es/sala-de-prensa/noticias/2026/04/renfe-recupera-servicios-ave-granada-malaga-zaragoza-barcelona
[catalogo]: https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia
[zips]: ../../backend/data/raw/renfe
[ouigo]: ../../backend/data/raw/ouigo/gtfs_ouigo_2026-11-12.zip
[fuentes]: ../../backend/data/curated/sources.json
[osm]: https://www.openstreetmap.org/relation/17684502
[osm-datos]: https://api.openstreetmap.org/api/0.6/relation/17684502/full.json
[osm-nudo]: https://api.openstreetmap.org/api/0.6/map.json?bbox=-3.668,40.298,-3.617,40.341
[geo]: ../../backend/src/oniel/geo.py
[carga]: ../datos.md#añadir-otra-línea
[monforte]: ../datos.md#cómo-se-cargó-el-enlace-de-monforte-del-cid
[grafo]: ../../backend/src/oniel/routing/graph.py
[grafo-visor]: ../../frontend/src/routing/graph.ts
[lector]: ../../backend/src/oniel/gtfs/reader.py
[pasos-este]: ../../frontend/public/data/segments/lav-madrid-barcelona--bif-vallecas-av--guadalajara-yebes.json
[pasos-sur]: ../../frontend/public/data/segments/lav-madrid-sevilla--bif-los-gavilanes--bif-torrejon-de-velasco.json
[api]: ../../backend/src/oniel/api/routers/routes.py
[paridad]: ../../backend/tests/test_routing.py
[pruebas-visor]: ../../frontend/e2e/recorridos.spec.ts
