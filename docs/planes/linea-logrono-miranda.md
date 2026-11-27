# Línea convencional Logroño – Haro – Miranda de Ebro

Quien consulte el atlas podrá seguir el Ebro desde Logroño hasta Miranda, abrir la ficha de Haro y distinguir los trenes que llegan a Miranda desde La Rioja de los que llegan desde Burgos. La carga comprende solo el tramo en servicio de la línea 700 de Adif entre ambas estaciones. Zaragoza, Barcelona, Burgos y Bilbao sirven para comprobar por dónde continúan los trenes sobre la red existente. [Ampliar la red][ruta] · [Línea 700 en servicio][tramos].

La implementación queda en la [incidencia #335][tarea], sin turno asignado. Conxo conserva el turno de datos. La referencia de este plan es el atlas de `2290fde6`, consultado el 27/11/2026, con horario estático del viernes 11/12/2026. [Base del estudio][base] · [Turno de Conxo][conxo].

## Qué vía incorporar

La 700 sale de Logroño hacia el oeste. Pasa por Fuenmayor, Cenicero, San Asensio y Briones antes de Haro. Desde Haro sigue por San Felices y entra a Miranda por el mismo lado que la vía de Pancorbo. **Haro es la única estación de viajeros que hay que añadir** para los tres horarios estudiados. Adif inventaría también esas instalaciones intermedias. Haro-El Pardo (81011) es otro apeadero, catalogado fuera de servicio. La bifurcación Castilla da acceso al ramal 704 hacia la bifurcación Rioja, fuera del recorrido de viajeros estudiado. [Dependencias de Adif][dependencias] · [Estación de Haro][adif-haro] · [Horarios archivados][zips].

| Lugar en el sentido Logroño → Miranda | Identidad y tratamiento |
| --- | --- |
| Logroño | Reutilizar `logrono`, parada 81100. La define Zaragoza–Castejón–Logroño en (−2,4408195°, 42,4575743°). Cortar el nuevo eje en la estación soterrada, donde acaba la línea existente. |
| Haro | Crear `haro`, parada 81002. El nodo OSM 1536500006 ya está en el extracto de Burgos–Vitoria. Su posición (−2,8491348°, 42,5837127°) se proyecta a 4 m del eje, a unos 49,346 km de Logroño. El punto de Renfe queda a 26 m del eje. Usar el primero para la estación y el código para unir el horario. |
| Aguja de entrada desde Haro | Nodo técnico sin parada comercial. En OSM es el 2127487436 (−2,9559250°, 42,6858496°). Aquí se incorpora la vía de Haro a la que el atlas ya recorre desde Burgos. |
| Miranda de Ebro | Reutilizar `miranda-de-ebro`, parada 11200. La define Burgos–Miranda–Vitoria en (−2,9411390°, 42,6907987°). Miranda–Bilbao ya usa ese mismo nodo con `shared: true`. Mantener una ficha común a los accesos hacia Burgos, Vitoria, Bilbao y Haro. |

Usar las coordenadas de las especificaciones propietarias al declarar nodos compartidos. El importador proyecta esas posiciones sobre el eje de cada línea. Retirar de Burgos–Miranda–Vitoria la única conexión `conv-miranda-logrono`, con `node_id: miranda-de-ebro` y `to_node_id: logrono`. La #264 hizo que esa declaración se viera desde ambos extremos. Actualizar en las tres especificaciones los textos que aún dicen que falta la línea. Comprobar los dos esquemas, el mapa y las dos fichas. [Zaragoza–Castejón–Logroño][ebro] · [Burgos–Miranda–Vitoria][burgos] · [Miranda–Bilbao][bilbao] · [#264][costura].

### El acceso a Miranda y los kilómetros

La relación OSM 9277501 tiene dos piezas. El grafo de vías de la primera llega desde el corte de Logroño (nodo 5554532811) hasta la aguja 2127487436, a **67,461 km** por vía y a 1,328 km en línea recta de la estación de Miranda. Los dos extractos ya archivados permiten recorrer el hueco completo entre vértices comunes. [Relación 700 archivada][raw700] · [Relación 100 archivada][raw100].

| Desde → hasta | Qué muestran las vías archivadas | Cómo contarlo en el atlas |
| --- | --- | --- |
| Logroño → Haro → aguja 2127487436 | 49,346 km hasta Haro y 18,115 km más hasta la aguja por la 700. | Son los dos tramos propios de la nueva línea. |
| 2127487436 → 2127487492 | 0,741 km continuos por la relación 18347132. Los 15 vértices están sobre el eje ya cargado de Burgos–Vitoria, entre sus km 82,609 y 83,350. | Partir Pancorbo–Miranda en la primera aguja. Conservar un solo tramo de acceso desde ella hasta la estación. |
| 2127487492 → Miranda | La segunda pieza de la 700 llega por las vías OSM 647047851 y 647047853 hasta el nodo 6077628638, donde empieza la geometría de Miranda–Bilbao (0,603 km). Por la 100 se recorren 0,599 km hasta su punto de estación. Son vías de andén distintas. | Se propone representar los últimos 600 m con el mismo acceso de estación que ya usa la 100. La ficha y un cierre de ese acceso se refieren al conjunto de vías representado. La vía de andén de cada tren queda pendiente. |

Para repetir la medida, trazar cada relación entre los pares de nodos de la tabla con `trace_osm_relation`. Proyectar la estación de Haro y las dos agujas con `Polyline.project` sobre las polilíneas completas. El recorrido físico candidato por la vía de andén de la 700 mide 68,805 km. En la representación propuesta, el comparador suma 67,461 km propios y 1,339 km existentes, **68,8 km entre estaciones**. La cobertura gana **67,461 km**. La suma de Pancorbo–aguja y aguja–Miranda recupera los 19,188 km anteriores con el redondeo a metros. [Construcción de líneas][construccion] · [Geometría][geo] · [Ficha actual del acceso][pancorbo].

La nueva línea se puede listar como `logrono-miranda` en «Aragón, Navarra y La Rioja». En el grafo, la 100 conserva la propiedad de la arista aguja–Miranda. La ficha de la 700 debe componer el itinerario Logroño–Haro–aguja–Miranda con los dos tramos propios y la referencia a esa arista. `shared: true` comparte la identidad de una estación. El modelo actual crea un tramo por cada pareja consecutiva de nodos de una especificación. Cortar la geometría propia en la aguja, resolver el acceso con `via` en los horarios y reutilizar el mismo identificador de tramo al componer ficha, esquema y recorrido. [Modelo de red][modelo] · [Precedente del acceso común en Salamanca][salamanca].

**Giros en la aguja.** Desde Haro y desde Pancorbo se puede entrar en Miranda. Para ir de Burgos a Haro por esta unión hay que llegar a la estación e invertir la marcha. El cálculo actual compara los rumbos a 500 m. Allí la curva abre 46,5° entre el brazo de Haro y el de Pancorbo, fuera del umbral de 30° para dos brazos del mismo lado. A 100 m son 8,4° entre ambos y más de 173° respecto al brazo de Miranda. Resolver el giro local con esa geometría documentada y comprobar en el índice, en Python y en el visor las dos entradas permitidas y la inversión en Miranda. [Cálculo de los lados][giros] · [Grafo y escenarios][grafo].

Las filas de Adif `017000080`, `017000090`, `017000100` y `017000110` identifican Logroño, Haro, San Felices y el acceso a Miranda como tramos de vía única. En el primero figuran PK 76,1 y 127,8 y una longitud inventariada de 49,413 km. El último termina en el PK 147,4. La especificación de Bilbao cita 145,2 como origen histórico en Miranda y la de Burgos usa el 458,913 de la 100. Conservar cada serie con su fuente y ámbito. La conciliación del PK de Miranda en la nueva ficha queda pendiente. El mapa 3 de Adif rotula 110 km/h en el corredor y el mapa 4 indica BAU con CTC (bloqueo automático en vía única, control centralizado) y ASFA. Las vías de la 700 analizadas hasta la aguja llevan ancho de 1.668 mm y 3 kV CC. En la carga, documentar los límites de cada atributo y las vías principales en los accesos con los mapas 3 y 4. [Filas de Adif][tramos] · [Mapas archivados, pp. 7–8][mapas] · [Especificación de Bilbao][bilbao].

## Qué trenes publica Renfe y qué se podrá comprobar

Se leyeron, sin importar, los ZIP del **8, 12 y 17/11/2026**. Para repetirlo, abrir cada uno con `read_feed`, seleccionar el día en `service_dates[trip.service_id]` (calendario semanal más altas y bajas) y recorrer `trip.stop_times` en orden. En las tres ediciones, todos los viajes con al menos dos de las paradas 81100, 81002 y 11200 tienen las tres consecutivas, en un sentido o en el otro. Hay **14 / 14 / 14** variantes hacia Miranda y **26 / 26 / 28** hacia Logroño en los archivos enteros. Tanto el **viernes 20/11** de la #264 como el **viernes 11/12** de la instantánea dan tres números por sentido en cada edición. [ZIP de Renfe][zips] · [Lector y calendario][lector].

Los filtros de las tres líneas vecinas ya seleccionan, en conjunto, las 40, 40 y 42 variantes. La carga debe enlazar esas paradas a la vía nueva conservando los identificadores de viaje y los días de circulación. [Selección de viajes][viajes].

Los ZIP del 8 y del 12 llaman *Media Distancia* a 37438/37437 y *Alvia* a 00438/00437. El del 17 los rotula *Regional* e *Intercity*, los nombres que se ven en la instantánea. Renfe identifica expresamente 37438 como servicio compartido con 00438, y 37437 con 00437. Conservar las dos ofertas, con sus cabeceras y permisos de subida y bajada. La unidad del censo de Oniel es el número publicado por edición y día. Un mismo número puede tener varios `trip_id` que el lector une. Por ejemplo, el 00438 del 11/12 reúne `0043812026-11-17`, `0043822026-11-17` y `0043832026-11-17`. [Nota de Renfe][renfe-obras] · [Unión de variantes][variantes].

Las horas siguientes son locales, del viernes **11/12/2026** según el ZIP del 17. Para el estado actual se cruzaron las llamadas de las estaciones con los servicios de cada tramo de la instantánea y se ejecutó el comparador con el índice completo y sus giros. Esto distingue un tren directo que vende Renfe de un camino que el atlas consigue atribuirle. [Índice][indice] · [Comparador][comparador] · [Ficha de Logroño][f-log] · [Ficha de Miranda][f-mir].

| Caso | Paradas y horas publicadas | Hoy en el atlas | Comprobación tras la carga |
| --- | --- | --- | --- |
| Regional 37438 a Miranda y 37437 a Zaragoza | 37438 sale de Delicias 10:48, sale de Logroño 12:55, para en Haro 13:36–13:37 y termina en Miranda 13:55. El 37437 sale de Miranda 16:54, para en Haro 17:11–17:12 y Logroño 17:55–17:57, y termina en Delicias 19:49. | Ambos figuran en Agoncillo–Logroño y en sus cabeceras. Haro aparece como destino con `node_id: null`. Entre Delicias y Miranda el recorrido más corto mostrado mide 701,2 km por Madrid. Ninguno de los dos regionales figura en ese camino. | Abrir Delicias ↔ Miranda. Cada número debe figurar en su sentido por Castejón, Logroño y Haro (unos 234,4 km), con las mismas horas y final comercial. La ficha de Haro debe mostrar a ambos a su hora y la de Miranda–Orduña debe seguir excluyendo estos dos números. |
| Alvia 00438 a Bilbao y 00437 a Barcelona | 00438 sale de Barcelona-Sants 08:50, comparte con 37438 el horario desde Delicias hasta Miranda, sale de allí 13:58 y llega a Bilbao 15:53. El 00437 sale de Bilbao 15:02, para en Miranda 16:52–16:54 y comparte con 37437 el horario hasta Delicias, de donde sale 19:52. Llega a Sants 22:13. | Figuran en Agoncillo–Logroño y Miranda–Orduña. Sants ↔ Bilbao enseña un directo por sentido y un primer recorrido de 1.118,8 km por el entorno de Madrid. El comparador deja el directo fuera de los recorridos mostrados. | Asignar 00438/00437 en su sentido al recorrido por Delicias, Logroño, Haro y Miranda hasta Bilbao (unos 656,9 km desde Sants y 338,4 desde Delicias). Deben figurar en los tramos propios de Haro y en Miranda–Orduña. Entre Sants y Bilbao solo el número de largo recorrido tiene ambas cabeceras. |
| Control por Burgos, 04187 y regreso 04186 | 04187 sale de Chamartín 06:55, para en Burgos 08:48–08:52, Miranda 09:57–09:59 y Llodio 11:30–11:32. Llega a Bilbao 12:05. El 04186 sale de Bilbao 06:53, para en Miranda 08:36–08:38 y Burgos 09:31–09:34 y llega a Chamartín 11:28. | El comparador ya los asigna al camino de 491,1 km por Segovia y Burgos. Figuran en Pancorbo–Miranda y Miranda–Orduña. | Mantener esa asignación en ambos sentidos, en los dos tramos que resulten de partir Pancorbo–Miranda y en Miranda–Orduña. Cero pasos de estos números en Logroño–Haro y Haro–aguja. Comparten el acceso final a Miranda. |
| De Burgos **hacia Logroño**, 04687 y regreso 04786 | El 04687 sale de Burgos 10:31, para en Miranda 11:35–11:42 y Haro 12:01–12:03 y llega a Logroño 12:50. El 04786 sale de Logroño 16:08, para en Haro 16:51–16:53 y Miranda 17:18–17:24 y llega a Burgos 18:29. | Las fichas de Burgos, Miranda y Logroño conservan las paradas. Son directos Chamartín ↔ Logroño, fuera del camino actual de 479,7 km por Zaragoza. | Deben aparecer por Burgos, con la parada e inversión en Miranda, y en ambos tramos propios de Haro. La comparación de Chamartín con Logroño debe poder asignarlos al camino por Miranda. En un viaje que entra y vuelve a salir por el mismo acceso, el itinerario recorre dos veces esa distancia y la ficha del tramo cuenta un único servicio. |
| Control de los regionales por Pamplona y Vitoria | El 18021 sale de Delicias 13:07, de Pamplona 15:26, de Vitoria 16:45 y termina en Miranda 17:17. El 18029 sale de Miranda 14:50 y pasa por Vitoria 15:20 y Pamplona 16:38 antes de llegar a Delicias 19:08. | Son directos entre Delicias y Miranda. Figuran en Miranda–Manzanos y salen de la línea del Ebro en Castejón. | Quedan fuera del recorrido por Haro y de su ficha en los dos sentidos. Las paradas intermedias distinguen qué regionales toman la rama navarra. |

**Atribución pendiente.** Las paradas y el orden sustentan el recorrido comercial. Los ZIP carecen de `shapes.txt`, de horas en las agujas y de vía de andén. La cartografía y los giros permiten proponer el camino entre paradas. El paso exacto de cada tren por una aguja, su vía de andén y su circulación efectiva ese día requerirían una marcha fechada u otra evidencia de explotación. En Logroño–Haro, donde ambos extremos son paradas consecutivas, se pueden mostrar las horas publicadas. En Haro–aguja–Miranda el paso por la aguja se interpola dentro del intervalo comercial. Para 00438 y 37438 debe quedar entre 13:37 y 13:55, y para 00437 y 37437 entre 16:54 y 17:11. Los avisos oficiales sí acreditan sustitución por carretera en fechas concretas, entre ellas el 21–22/11 y el 12–13/12. Los dos viernes de control quedan fuera de esos intervalos. Al cargar, revisar las fechas con Adif y Renfe y registrar la interrupción con su vigencia y transporte alternativo. [Aviso de Adif][adif-obras] · [Servicios y fechas de Renfe][renfe-obras].

## Orden de implementación y aceptación

1. **Construir y medir.** Registrar fuentes y originales fechados, dar de alta Haro, partir el acceso de la 100, referenciarlo desde la 700 y retirar el croquis al disponer del camino continuo. Verificar un único marcador por estación, dos tramos nuevos de vía propia, una sola geometría y ficha del acceso común, y continuidad con la 700 hacia Bilbao. La ficha de línea suma el recorrido de punta a punta. La cobertura suma aristas físicas únicas. Repetir la medición si cambia la geometría de partida. [Procedimiento «Añadir otra línea»][procedimiento].
2. **Asignar con las paradas.** En el Ebro, conservar la regla `miranda-por-logrono` (Calahorra 81108 → Logroño 81100 → Haro 81002, o inversa) y el camino por defecto de Miranda vía Castejón cuando el viaje pasa por Pamplona. En la línea nueva, seleccionar 81100–81002–11200 y su inversa. En la 100, incorporar los viajes que solo usan aguja–Miranda, distinguiéndolos de los que también pasan por Burgos o Vitoria. En Miranda–Bilbao, completar las salidas de Haro y Logroño vía el acceso común y la línea nueva. Revisar los `via` recíprocos del Ebro y de la LAV de Barcelona hasta las paradas que cubre cada tren. Cada salto ha de compartir nodo y cada servicio debe conservar el orden de paradas, las horas y los permisos de su edición. [Reglas del Ebro][ebro] · [Selección de viajes][viajes].
3. **Comprobar el reparto.** El 11/12 se esperan en los tramos propios y la ficha de Haro los números **00438, 37438 y 04786 hacia Miranda**, y **00437, 37437 y 04687 hacia Logroño**. En cada cabecera ya se ofrecen tres directos hacia la otra y tres hacia Haro. Al cargar, Haro debe quedar enlazada desde ambas. Hoy el mínimo entre cabeceras es 866,9 km por Madrid, sin ninguno de esos directos asignado. Repetir la comparación en ambos sentidos y comprobar los seis en el nuevo camino de 68,8 km. Las distancias previstas en el plan proceden de introducir los dos tramos y el giro de la aguja en una copia en memoria del grafo. [Comparación entre cabeceras][ver-comparacion] · [Ficha actual de Miranda][f-mir].
4. **Conciliar los tramos vecinos.** En el día de referencia hay 16 servicios en Agoncillo–Logroño, 29 en Pancorbo–Miranda, 31 en Miranda–Manzanos y 8 en Miranda–Orduña. En el modelo propuesto, Pancorbo–aguja conserva los 29 y el acceso aguja–Miranda lleva **33 servicios distintos**. Es la unión de esos 29 con los seis de Haro, con 04687 y 04786 presentes en ambos grupos. Las otras tres fichas conservan sus conjuntos de números. Revisar por edición la clave `(dataset_id, service_id, segment_id)`, la continuidad de los tiempos y el límite del modelo para un servicio que recorre dos veces el mismo tramo. [Agoncillo–Logroño][agoncillo] · [Pancorbo–Miranda][pancorbo] · [Miranda–Manzanos][manzanos] · [Miranda–Orduña][orduna].
5. **Verificar la entrega de datos cuando tenga turno.** Importar desde una base vacía. Ejecutar `oniel-data validate` con la especificación y para toda la red, contrastar los tres ZIP, los giros y los controles de la tabla. Probar el comparador y las fichas en Playwright estático y con la API local. Simular el cierre del acceso común y el de un tramo propio de Haro, revisar los rodeos que introduce el nuevo anillo y actualizar los totales de tramos sin alternativa. Regenerar una vez la instantánea, revisar índice, fichas, histórico, pesos y recuentos, y actualizar en esa futura PR la documentación de red. [Pruebas del Ebro][test-ebro] · [Pruebas de Miranda–Bilbao][test-bilbao] · [Método del comparador][metodo].

## Fuentes y condiciones de uso

Consulta del 27/11/2026. La futura carga ampliará la cobertura de las entradas ya registradas y archivará las consultas nuevas con editor, licencia, fecha y ámbito. [Registro de Oniel][fuentes].

| Fuente pública | Uso en este plan y condiciones |
| --- | --- |
| Colaboradores de OpenStreetMap, relaciones 9277501 y 18347132 y nodo de Haro | Geometría, agujas, coordenadas y etiquetas, ODbL 1.0 con atribución. Reutilizar `osm-relation-9277501` (20/11), `osm-relation-18347132` y `osm-instalaciones-burgos-vitoria` (17/11). [Línea 700][osm700] · [Línea 100][osm100] · [Estación archivada][raw-haro] · [Licencia][odbl]. |
| Adif, capas «Tramos en servicio» y «Dependencias» | Topología, dependencias, estados, PK y longitudes de catálogo. Permiten cualquier uso con la mención «© Administrador de infraestructuras ferroviarias». [Condiciones de tramos][cond-tramos] · [Condiciones de dependencias][cond-dep]. |
| Adif y Adif Alta Velocidad, Declaración sobre la Red, ficha de Haro y avisos | Contraste de atributos, código de estación y fechas de obras. Consulta pública, © de sus editores. Usar el original ya archivado de los mapas para la verificación. [Mapas de la DR 2026][mapas] · [Ficha de Haro][adif-haro] · [Aviso de obras][adif-obras]. |
| Renfe Viajeros, GTFS AV/LD/MD y comunicación de obras | Horarios planificados, licencia CC BY 4.0. La nota editorial de Renfe acredita los servicios compartidos y el plan alternativo, con © Renfe. [Catálogo público][gtfs] · [CC BY 4.0][ccby] · [Nota de Renfe][renfe-obras]. |
| Colaboradores de Wikipedia, fuente de las especificaciones contiguas | La referencia histórica `wikipedia-linea-casetas-bilbao` documenta el origen de PK empleado en Miranda–Bilbao. CC BY-SA 4.0. Las revisiones utilizadas constan en el registro. [Registro de fuentes][fuentes] · [CC BY-SA 4.0][ccbysa]. |

[tarea]: https://github.com/ebotiab/Oniel/issues/335
[conxo]: https://github.com/ebotiab/Oniel/issues/322
[costura]: https://github.com/ebotiab/Oniel/issues/264
[base]: https://github.com/ebotiab/Oniel/commit/2290fde60f24bda7c6278d556baf35dfb5d6f5c5
[ruta]: ../hoja-de-ruta.md#ampliar-la-red
[procedimiento]: ../datos.md#añadir-otra-línea
[grafo]: ../simulacion.md#grafo-y-escenarios
[metodo]: ../simulacion.md#comparar-recorridos
[salamanca]: linea-medina-del-campo-salamanca.md#geometría-reproducible-y-comprobación-de-la-cabecera-salmantina
[ebro]: ../../backend/data/curated/zaragoza-castejon-logrono.json
[burgos]: ../../backend/data/curated/burgos-miranda-vitoria.json
[bilbao]: ../../backend/data/curated/miranda-bilbao.json
[fuentes]: ../../backend/data/curated/sources.json
[raw700]: ../../backend/data/raw/osm/relation_9277501_linea_700_casetas_bilbao_2026-11-20.json
[raw100]: ../../backend/data/raw/osm/relation_18347132_linea_100_madrid_hendaya_2026-11-17.json
[raw-haro]: ../../backend/data/raw/osm/instalaciones_burgos_vitoria_2026-11-17.json
[mapas]: ../../backend/data/raw/adif/dr-adif-av-2026-mapas_2026-11-12.pdf
[zips]: ../../backend/data/raw/renfe
[lector]: ../../backend/src/oniel/gtfs/reader.py
[variantes]: ../../backend/src/oniel/gtfs/variants.py
[viajes]: ../../backend/src/oniel/gtfs/trips.py
[giros]: ../../backend/src/oniel/routing/turns.py
[construccion]: ../../backend/src/oniel/network/build.py
[geo]: ../../backend/src/oniel/geo.py
[modelo]: ../../backend/src/oniel/network/spec.py
[comparador]: ../../frontend/src/app/recorridos.ts
[indice]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/index.json
[f-log]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/nodes/logrono.json
[f-mir]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/nodes/miranda-de-ebro.json
[agoncillo]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/segments/zaragoza-castejon-logrono--agoncillo--logrono.json
[pancorbo]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/segments/burgos-miranda-vitoria--pancorbo--miranda-de-ebro.json
[manzanos]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/segments/burgos-miranda-vitoria--miranda-de-ebro--manzanos.json
[orduna]: https://github.com/ebotiab/Oniel/blob/2290fde60f24bda7c6278d556baf35dfb5d6f5c5/frontend/public/data/segments/miranda-bilbao--miranda-de-ebro--orduna.json
[test-ebro]: ../../backend/tests/test_zaragoza_logrono_pamplona.py
[test-bilbao]: ../../backend/tests/test_miranda_bilbao.py
[ver-comparacion]: https://oniel.vercel.app/recorridos/logrono/miranda-de-ebro
[osm700]: https://www.openstreetmap.org/relation/9277501
[osm100]: https://www.openstreetmap.org/relation/18347132
[odbl]: https://www.openstreetmap.org/copyright
[cond-tramos]: https://www.arcgis.com/home/item.html?id=4ec7c0fb3cab42b0b488d65e65eeb7aa
[cond-dep]: https://www.arcgis.com/home/item.html?id=b181bd5b69bb40aca11892a6361c39f5
[tramos]: https://services7.arcgis.com/XTupIrLX53AjaJqO/arcgis/rest/services/Tramos_en_servicio_Adif_p%C3%BAblico/FeatureServer/0/query?where=CODTRAMO+IN+%28%27017000080%27%2C%27017000090%27%2C%27017000100%27%2C%27017000110%27%29&outFields=CODTRAMO%2CDEPORIGEN%2CDEPDESTINO%2CPKI%2CPKD%2CLONGITUD%2CCOD_TIPO_V&returnGeometry=false&f=pjson
[dependencias]: https://services7.arcgis.com/XTupIrLX53AjaJqO/arcgis/rest/services/Dependencias_Adif_p%C3%BAblico/FeatureServer/0/query?where=COD_TRAMO+IN+%28%2717000080%27%2C%2717000090%27%2C%2717000100%27%2C%2717000110%27%29&outFields=NOMBRE%2CCOD_DEPEND%2CCOD_ESTADO&returnGeometry=false&f=pjson
[adif-haro]: https://www.adif.es/w/81002-haro
[adif-obras]: https://www.adif.es/w/obras-miranda-de-ebro-logrono?redirect=%2Fviajeros%2Favisos
[renfe-obras]: https://grupo.renfe.com/es/es/sala-de-prensa/noticias/2025/11/renfe-programa-300-autobuses-por-obras-entre-logrono-miranda-de-ebro
[gtfs]: https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia
[ccby]: https://creativecommons.org/licenses/by/4.0/
[ccbysa]: https://creativecommons.org/licenses/by-sa/4.0/
