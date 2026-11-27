# Línea convencional Ávila – Salamanca

**Especificación para la [incidencia de implementación #316](https://github.com/ebotiab/Oniel/issues/316). Investigación del 26 de noviembre de 2026.** El recorrido que falta en el visor sale de Ávila, pasa por Peñaranda de Bracamonte y llega a Salamanca. Los regionales procedentes de Madrid-Príncipe Pío continúan desde la estación principal hasta el apeadero de Salamanca-La Alamedilla. En sentido contrario parten de la principal. La línea administrativa termina en Salamanca. Para representar el viaje completo hacen falta también la entrada por Pinar de las Rozas y un corto tramo de otra línea en Salamanca.

Se examinó el [`main` b0f3ad5][base] y se buscó «Salamanca» en las incidencias y PR abiertas y cerradas. [#211](https://github.com/ebotiab/Oniel/issues/211) dejó la salida a trazos. [#308](https://github.com/ebotiab/Oniel/issues/308) y su [PR #315, revisión df3c888][pio] aportan Príncipe Pío–Pinar y dejan Salamanca como destino comercial exterior. Ambas estaban abiertas en la consulta. [#310, Grisén](https://github.com/ebotiab/Oniel/issues/310), también abierta, trata del enlace de la línea del Ebro. La investigación de ambos accesos puede avanzar en paralelo. Para implementar, partir del `main` que ya incluya #308, comprobar qué más se ha incorporado y acordar un solo turno de datos con Grisén y los refrescos GTFS.

## Infraestructura y estaciones

Adif administra la **línea 122 Salamanca – Ávila**, identificada también como **01-122 Ávila–Salamanca** en el catálogo de la Red Ferroviaria de Interés General. Tiene **111,1 km de referencia, vía única, ancho ibérico de 1.668 mm y tronco sin electrificar**. El mapa 3 de la Declaración sobre la Red sitúa **155 km/h** sobre el propio Ávila–Salamanca. El mapa 4 indica **ASFA convencional**, **BLAU** (bloqueo de liberación automática en vía única) y **CTC** (control de tráfico centralizado). Este nivel de detalle corresponde al corredor. Las vías de estación y el acceso final tienen límites distintos. [Catálogo del BOE][boe] · [Declaración de Adif, clasificación y longitud][dr] · [mapas 3 y 4, pp. 7 y 8 del PDF conservado en Oniel][mapas].

| Instalación, en sentido desde Ávila | Código de parada Renfe | PK de referencia (km) | Identidad propuesta en Oniel |
|---|---|---|---|
| Ávila | 10400 | Origen del kilometraje de la 122. La 100 ya usa 120,6 | Reutilizar `avila` |
| Cardeñosa de Ávila | 34002 | 15,707 | `cardenosa-de-avila` |
| San Pedro del Arroyo | 34005 | 36,103 | `san-pedro-del-arroyo` |
| Crespos | 34007 | 47,656 | `crespos` |
| Narros del Castillo | 34008 | 55,670 | `narros-del-castillo` |
| Peñaranda de Bracamonte | 34010 | 70,792 | `penaranda-de-bracamonte` |
| Villar de Gallimazo | 34011 | 80,481 | `villar-de-gallimazo` |
| Babilafuente | 34012 | 92,159 | `babilafuente` |
| San Morales | 34013 | 97,648 | `san-morales` |
| Aldealengua | 34014 | 102,789 | `aldealengua` |
| Salamanca, estación principal, también llamada Vialia | 30100 | 76,825 en el acceso desde Medina. Pendiente el PK exacto de la instalación en la 122 | `salamanca` |
| Salamanca-La Alamedilla, apeadero urbano después de la principal | 30110 | 0,900 en la kilometración desde Salamanca hacia Fuentes de Oñoro | `salamanca-la-alamedilla` |

Los PK intermedios y los dos de la 120 se leen en la lámina de Salamanca del esquema de mantenimiento. Ávila figura como origen en el perfil longitudinal. Cada línea conserva su propio origen de distancias. El mismo esquema sitúa Monsalupe (23,620) y Aveinte (31,013) en el trazado. Ninguno aparece como parada en los tres horarios comprobados. Revisar su función actual antes de darles ficha. En Babilafuente hay instalaciones de mercancías y un acceso industrial a la planta de bioetanol. Su ramal queda fuera del recorrido de viajeros. La bifurcación La Serna, PK 2,664 después de La Alamedilla hacia Tejares, queda fuera del acceso desde Medina descrito a continuación. [Esquema de Adif, lámina «Salamanca»][esquema] · [perfil de la 122, Ministerio de Transportes][perfil] · [instalaciones de servicio de Adif][instalaciones] · [proyecto regional de Babilafuente][babilafuente].

### Una línea en la lista y una vía por tramo en el grafo

Crear una entrada principal `avila-salamanca`, «Línea convencional Ávila – Salamanca», en la zona existente `castilla-y-leon`. La ficha debe explicar hasta dónde llega la 122 y por qué el esquema continúa a La Alamedilla por la 120. Usar Adif como administrador y Renfe como operador de los horarios observados. El orden en la lista sigue las reglas actuales de zona, tipo y longitud. Conservar el enlace de Príncipe Pío bajo `madrid-avila-valladolid`. [Modelo de zonas y líneas](../datos.md#zonas) · [reglas del acceso de Príncipe Pío][enlace].

1. **En Ávila**, conservar la ficha, posición e ID de `avila` y el recorrido desde Chamartín. La aguja T6 (OSM `2055712105`) cae sobre la polilínea exportada Ávila–Arévalo, a 0,448 km de la estación y a menos de 0,1 m del eje proyectado. Se propone partir ese tramo en `bif-avila-salamanca`. Recorrer estación–aguja por la 100 una sola vez y comenzar allí las aristas propias de la línea nueva. En su esquema dar acceso a la ficha de Ávila mediante la conexión compartida. En la 100, los trenes hacia Peñaranda deben alcanzar la aguja y abandonar allí el camino a Arévalo. Recalcular las referencias al tramo partido y comprobar los giros con el sentido físico de las agujas. [Especificación de la 100][conv] · [T6 en OSM](https://www.openstreetmap.org/node/2055712105).
2. **En Salamanca**, reservar `bif-acceso-salamanca` para la unión al itinerario de la 120 elegido en la cabecera este. Es un ID del modelo, sin nombre oficial de dependencia acreditado. Crear dos aristas consecutivas, aguja–`salamanca` y `salamanca`–`salamanca-la-alamedilla`. Un futuro acceso de Medina terminará en la aguja y reutilizará esas aristas y fichas. El itinerario seleccionado corresponde a una de las vías posibles de llegada a la principal. Hay vías paralelas en la playa de estación. El GTFS identifica las paradas, sin fijar un andén o aguja para cada tren. [OSM, entrada compartida](https://www.openstreetmap.org/node/33246283) · [Adif, estación][sal] · [Adif, apeadero][ala].
3. **Conexiones a trazos.** Sustituir `conv-avila-salamanca`. Mantener `conv-medina-salamanca`, orientado al empalme de la cabecera este mediante `to_node_id` y una sola conexión bidireccional. Conservar `enlace-medina-salamanca` de `lav-olmedo-ourense` como acceso exterior desde Medina del Campo AV. Mantener las salidas hacia Segovia y Zamora y las de #315. Más allá de La Alamedilla quedaría la continuación hacia Tejares y Fuentes de Oñoro. Los croquis pendientes se excluyen de las rutas y del cálculo de alternativas. [Costuras del modelo](../datos.md#las-costuras-entre-líneas) · [línea de Olmedo][olmedo].

### Cadena de geometría que se ha medido

Se descargaron en una carpeta temporal los originales JSON de la API 0.6 de OSM. Para repetir la medida, abrir `https://api.openstreetmap.org/api/0.6/relation/ID/full.json` para las tres relaciones de la tabla. Seleccionar **solo los miembros de tipo vía con `railway=rail`**, enlazar cada par de nodos consecutivos por ID, ponderar por distancia de Haversine (radio 6.371 km) y obtener el camino más corto entre los nodos indicados, en el orden de las filas. El camino inverso utiliza los mismos nodos. Los enlaces de OSM permiten consultar el historial si cambia un miembro. Antes de incorporar los originales, guardar la fecha, las versiones de los objetos y el resultado de la comprobación de conectividad.

| Recorrido de comprobación | Selección, nodos y vías de control | Distancia medida |
|---|---|---:|
| Parada de Ávila → T6 | R-20, relación 1210118 v118, `244749631 → 2055712105`. El recorrido pasa por las vías `22790074`, `22790073`, `23564552` y `1222196685`. La estación del atlas representa varias vías con una sola posición. En el grafo usar el eje existente hasta T6 | 0,451 km en OSM |
| T6 → entrada este de Salamanca por Cardeñosa, Peñaranda y Babilafuente | Relación 6016263 v34, `2055712105 → 4033375026`. Pasa por la aguja `2055712107`, la vía `23564572`, la vía `234415621` después de San Pedro y la `648242614` al entrar en Salamanca | 109,804 km |
| Entrada este → confluencia sobre la 120 | R-20, vía diagonal `400830393`, `4033375026 → 33246283`. Carece de `ref`. El selector por relación y extremos permite recuperarla | 0,087 km |
| Confluencia → parada de Salamanca | En las relaciones 1210118 y 6016262 v49 coinciden las vías `1513727190`, `463078624` y `400830385`, desde `33246283` hasta `33246281` | 0,481 km |
| Salamanca → La Alamedilla | En la 6016262, `33246281 → 495082202`, por `400830386`, `23511251`, `400830384`, `46951240`, `47091988`, `39706653` y parte de `39706654` | 0,833 km |

Los tres enlaces entre selecciones tienen el **mismo nodo en ambas partes**. Como control independiente, en la R-20 hay un camino continuo de **110,823 km** entre las paradas OSM de Ávila y Salamanca y de **111,657 km** hasta La Alamedilla. Se recortó la relación al salir de Ávila porque su cabecera madrileña incluye Chamartín. La 6016263 comienza en T6 y al final pasa por otra vía de estación. Es una relación `route=train`, con `network=Renfe Alvia`. Esa etiqueta no clasifica los trenes actuales. El segmento común con Medina empieza en el nodo `33246283` para **este** camino. La proximidad de los dos corredores antes de la diagonal no justifica unirlos. [R-20][r20] · [vías por Ávila][r122] · [vías por Medina][r120].

**Atributos por sección.** El mapa 3 confirma la máxima de corredor. Las vías OSM de la 122 muestran 85–105 km/h en el primer sector y 155 km/h en vías concretas a partir del entorno de San Pedro. Hay miembros sin `maxspeed`. Obtener máximas y velocidad predominante por longitud en cada tramo construido. Donde falte respaldo dejar el valor ausente. El campo `DesignSpeed` de INSPIRE es de diseño. [Mapas de Adif][mapas] · [vía de 85 km/h](https://www.openstreetmap.org/way/23564572) · [vía de 155 km/h](https://www.openstreetmap.org/way/234415621) · [red INSPIRE de Adif][inspire].

El BOE y el mapa distinguen el tronco de vía única sin electrificar. En la cabecera de Ávila, OSM etiqueta la breve vía `400877194` con 3 kV CC. En Salamanca, `4033375032` marca en OSM el cambio entre vía sin electrificar y catenaria de 25 kV en `648242614`. Después aparece la misma tensión en la diagonal y en la vía elegida de la 120 hasta el apeadero. Adif confirma la electrificación en servicio desde Medina hasta Salamanca y documenta por separado las obras hacia Fuentes de Oñoro. **Queda por confirmar la puesta en tensión y el límite operativo de cada vía de cabecera**, además de las velocidades locales que faltan. Distinguir vía general, vías paralelas de líneas distintas y vías de estación. Registrar `tracks`, ancho, electrificación, protección, bloqueo y mando con su ámbito. No extender BLAU ni los 155 km/h al interior de las estaciones por defecto. [BOE][boe] · [Adif, energía en la 120][energia] · [OSM, vía de entrada](https://www.openstreetmap.org/way/648242614).

## Servicios del horario y controles de itinerario

Se leyeron **los seis ZIP** del [registro de fuentes de Oniel][fuentes]. Para repetir el censo sin importar nada, usar `oniel.gtfs.reader.read_feed` con los prefijos, alias y campo de número registrados para cada fichero. En cada viaje ordenado por `stop_sequence`, buscar `30100`, `30110` o una de las nueve paradas interiores. Agrupar por las paradas distintivas de la tabla, origen, destino y producto. Para un día concreto, exigir pertenencia a `feed.service_dates[trip.service_id]`. El lector expande `calendar.txt`, aplica altas y bajas de `calendar_dates.txt` y reúne las variantes coincidentes por número y día. Las ventanas de días distintos conservan su identidad. [Lector y regla de variantes](../../backend/src/oniel/gtfs/variants.py).

| Itinerario observado en Renfe | Viajes del fichero completo tras normalizar, 08 / 12 / 17 noviembre | Programados el jueves 26/11 en el ZIP del 17 |
|---|---:|---:|
| Príncipe Pío `10000` → Ávila `10400` → Peñaranda `34010` → Salamanca `30100` → La Alamedilla `30110` | 37 / 36 / 36 | 7 |
| Salamanca `30100` → Peñaranda → Ávila → Príncipe Pío | 36 / 35 / 35 | 7 |
| Por Medina **convencional** `10500`, desde/hacia Valladolid, Palencia o Zaragoza, ambos sentidos | 44 / 41 / 41 | 14, de los cuales 5 continúan desde Salamanca a La Alamedilla |
| Por Segovia-Guiomar `08004` y Medina **AV** `08240`, entre Chamartín `17000` y Salamanca `30100`, ambos sentidos | 50 / 50 / 50 | 8, todos con cabecera salmantina en la principal |

Ouigo, Iryo y SNCF aportan cero coincidencias en sus respectivos ficheros. Los tres GTFS de Renfe son ediciones superpuestas. La consulta de un día elige la edición aplicable por fuente. Sumar las tres columnas históricas multiplicaría los mismos trenes. Los trenes de Príncipe Pío por Ávila llevan el producto **Media Distancia** en los ficheros del 8 y 12 y **Regional** en el del 17. Los de Chamartín por Medina AV pasan de **Alvia** a **Intercity**. Conservar los números con ceros iniciales. [Horarios de Renfe][gtfs] · [conjuntos y selección por fecha](../datos.md#conjuntos-de-datos).

**Variantes por Ávila en el fichero del 17.** Todos paran en Villalba `10200`, El Escorial `10203`, Ávila, Peñaranda y Salamanca. Esta tabla recoge también las variantes que circulan en días distintos al de control.

| Sentido y parada en la 122 | Números | Diferencias de recorrido |
|---|---|---|
| Príncipe Pío → La Alamedilla, con las nueve intermedias | 18901, 18921 | Paran en el orden del inventario. El 26/11 figura 18901 y el sábado 28/11 figura 18921 |
| Príncipe Pío → La Alamedilla, solo Peñaranda entre Ávila y Salamanca | 18903, 18905, 18907, 18909, 18911, 18913 | 18907 y 18913 paran además en la sierra entre El Escorial y Ávila |
| Salamanca → Príncipe Pío, con las nueve intermedias | 18904 | Sale de la principal. Recorre las nueve en orden inverso |
| Salamanca → Príncipe Pío, solo Peñaranda entre ambas capitales | 18900, 18902, 18906, 18908, 18910, 18912 | 18912 tiene dos secuencias en la sierra, una omite Zarzalejo, Robledo de Chavela y Santa María de la Alameda-Peguerinos (`10204/10205/10206`) |

Los días de estos trenes en el ZIP del 17 abarcan del **16/11/2026 al 24/01/2027**. En esa ventana 18900/02/03/04/07/09/12/13 tienen 70 días cada uno. 18901/05/06 tienen 45 laborables, con excepciones como el 7 y 8 de diciembre. 18908 tiene 68 días, 18910 tiene 55, 18911 tiene 58 y 18921 tiene 26. Por ejemplo, el sábado 28/11 hay 11 trenes por Ávila entre ambos sentidos y el viernes 11/12 hay 14. Consultar el calendario por número y fecha. Un fin de ventana solo delimita la cobertura de esa edición.

**Reglas que deben encajar.**

- La 100 exige al menos dos paradas en nodos y una estación propia. En la base, las nueve paradas `340xx` y ambas salmantinas son salidas por `avila`. Sus tres excepciones `salamanca-por-medina-30100/32002/32001` detectan los pares consecutivos `10500 ↔ 30100/32002/32001` (Salamanca, El Carpio o Campillo) y sacan ambas salmantinas por `medina-del-campo`. Conservar esas excepciones. Para el patrón por Ávila, mover la salida al empalme T6 y resolver las paradas interiores por `via` de la nueva línea. Asignar recíprocamente `10400` y las paradas hacia Madrid a la 100 desde T6. Al resolver Príncipe Pío, el siguiente salto después de la 100 es el enlace en Pinar. [100 en la base][conv] · [100 revisada en #315][conv315].
- #315 requiere `10000` y `10200` en el enlace. Su regla `principe-pio-villalba` usa ese par consecutivo, con paso estimado en Pinar. La variante `principe-pio-aravaca` recorta `10000,10001,10002,10005,10100` hasta Pinar cuando hay paradas intermedias. Los de Salamanca por Ávila estudiados usan la primera. Conservar `link_towards: las-matas` y el recorte de los trenes de Príncipe Pío por Atocha en la 100. La cabecera de Chamartín de la 100 sigue dando acceso a Ávila. [Especificación de #315][enlace].
- Para el tramo propio, seleccionar recorridos con una parada exclusiva (Peñaranda está en **todos** los observados) y al menos dos paradas en la línea. Los trenes que solo alcanzan Salamanca desde Medina necesitan reglas específicas de entrada/salida en `bif-acceso-salamanca`. Los pares consecutivos observados junto a `30100` son `08240` (AV), `10500` (Medina convencional), `32004` (Cantalapiedra), `32008` (Gomecello) y `32009` (Moriscos). Recortar el cálculo al lado salmantino y mantener `30110` cuando siga en el horario. La parte exterior se trata como salida por Medina, con distancia de vía solo si se documenta. Probar cada patrón en el sentido publicado. Si cambia el GTFS, revisar las secuencias antes de añadir excepciones.
- Controles por Medina convencional: regionales 18300/02/04/06/08/10/12/14/16/18/24, 37431/37432 e Intercity 00631/00632 (Zaragoza). Por Medina AV: 04809/04868/04898/04899/04909/04918/04929/04958/04969/04988. La coincidencia de horas de 00631 con 37431 tampoco basta para fusionar números distintos. La pertenencia a varias líneas conserva el viaje normalizado del mismo conjunto y sus permisos de subida y bajada. El 18901 llega a Salamanca a las 10:40 y sale a las 10:42 solo para dejar viajeros, antes de su terminal de las 10:45. La ficha de destinos directos debe respetar esa restricción.

### Horario publicado y circulación efectiva

El 26/11 se revisaron los avisos de Adif, el estado de la red y los paneles de las dos estaciones salmantinas y Ávila. No se identificó un corte vigente del tronco Ávila–Salamanca en las páginas consultadas. En el acceso **Madrid–Ávila**, el 15/11 se anunció transporte por carretera entre El Escorial y Robledo de Chavela. En la consulta del 26/11 Adif comunicaba circulación restablecida por una vía entre Robledo y Zarzalejo. El catálogo de restricciones del 26/11 documenta programación, que puede cambiar. Verificar aviso, tramo y fecha al cargar datos. El boletín de Renfe para la huelga del 17/11 calificó el 18901 de afectado aunque figure en el calendario. Un autobús alternativo se describe en el aviso de ese día, sin generar pasos de tren en la vía. [Panel de Peñaranda del 15/11][pen15] · [Adif, estado][estado] · [avisos][avisos] · [restricciones][rtc] · [Renfe, servicios del 17/11][huelga].

Para el **11 al 13 de diciembre de 2026**, el pliego de Renfe del expediente 2026-04060 prevé autobuses entre El Escorial, Villalba y Príncipe Pío por obras. Coincide con el día de referencia del visor (11/12). El recuento GTFS de ese viernes acredita la oferta programada. Para describir el viaje efectivo hará falta el aviso comercial definitivo con los servicios y tramos afectados. [Renfe Viajeros, especificaciones técnicas del transporte alternativo, pp. 1–2][pat].

## Aceptación de la futura implementación

**Contraste con el acceso de Príncipe Pío ya fusionado.** En `main` a73d8f4, la suma del enlace hasta Pinar y la parte de la 100 hasta Ávila mide 120,57794 km. La relación R-20 v118 archivada da 110,82341 km desde la parada de Ávila hasta la de Salamanca y 111,65669 km hasta La Alamedilla. Trazada al revés, devuelve los mismos vértices en orden inverso. Esta comprobación independiente da 231,40135 y 232,23463 km desde Príncipe Pío. La diferencia de 0,83329 km es el recorrido urbano. Los 232,3 km indicados abajo procedían de sumar cifras previamente redondeadas. En un ensayo local de infraestructura con el tramo compartido de la 100, se miden 231,39842 y 232,23170 km. La API local y el motor de recorridos del visor, sobre el mismo índice, redondean a 231,4 y 232,2 km en ambos sentidos. El tiempo sin paradas queda ausente al faltar velocidades locales de la cabecera salmantina.

El horario del día de control ya se importa con el mismo identificador de viaje en Príncipe Pío y en la 100. La prueba `test_avila_salamanca.py` comprueba sobre cada original de Renfe las terminales, los productos y la unicidad por número y día. En una base vacía con la red previa a la 122, el importador conserva 5.272, 5.124 y 5.057 viajes de Renfe en las ediciones del 8, 12 y 17 de noviembre, respectivamente. Estas son las cifras de partida para reconciliar la ampliación. Se cotejaron por viaje las 676, 658 y 658 paradas comerciales, sus horas y permisos, y los 1.016, 966 y 902 servicios-día de los regionales por Ávila en esas ediciones.

El GTFS del 17 permite contrastar el tiempo comercial del 26/11. Se toma la salida de una parada que admite subida y la llegada posterior del mismo viaje a una parada que admite bajada.

| Origen | Destino | Viajes directos | Tiempo comercial mínimo |
|---|---|---:|---:|
| Madrid-Príncipe Pío | Salamanca | 7 | 2 h 34 min |
| Madrid-Príncipe Pío | Salamanca-La Alamedilla | 7 | 2 h 39 min |
| Salamanca | Madrid-Príncipe Pío | 7 | 2 h 38 min |
| Salamanca-La Alamedilla | Madrid-Príncipe Pío | 0 | — |
| Salamanca | Salamanca-La Alamedilla | 0 | — |

Los doce viajes que recorren el tramo urbano tienen subida prohibida y bajada permitida en Salamanca principal. Un viajero que ya está en el tren puede continuar al apeadero. Quien empieza en la principal carece de destino directo en el apeadero ese día. [GTFS de Renfe][gtfs]

1. **Inventario y geometría.** Archivar las consultas originales, registrar fuentes, licencias, fecha y ámbito. Repetir la cadena por IDs en ambos sentidos con cero saltos. Cotejar los empalmes, la posición de las nueve paradas interiores y el sentido de las agujas. Conservar las fichas de Ávila y Pinar, el acceso de Chamartín, dos fichas salmantinas y una sola arista física por trecho. Documentar PK, longitud medida y secciones de atributos por separado. Si un atributo obligatorio carece de respaldo, resolverlo antes de importar.
2. **Mapa, esquema y comparador.** El buscador y la lista de Castilla y León llevan a la línea principal, sus estaciones, tramos y fuentes en escritorio y móvil. Desde Príncipe Pío hasta Salamanca deben resultar aproximadamente **231,4 km**, y hasta La Alamedilla **232,3 km**, en ambos sentidos. Son controles geométricos redondeados (120,6 km hasta Ávila según #315 más la cadena medida), sujetos al recorte definitivo. La diferencia urbana es unos 0,83 km. Comparar kilómetros y tiempos en modo estático y con la API. El tiempo sin paradas se calcula tramo a tramo con velocidades justificadas o queda ausente cuando falten. No crear una alternativa ferroviaria mediante el croquis de Medina.
3. **Censo y continuidad.** Reproducir por edición los 73/71/71 viajes por Ávila, sin aumentar el total de viajes únicos por volver a representar los mismos regionales. Con el horario del 17, el 26/11 deben contarse **14** por el interior de la 122 y **12** en Salamanca–La Alamedilla (7 por Ávila + 5 por Medina). El 18904, el 04899 de Chamartín y el 00631 de Zaragoza terminan o empiezan en la principal y no recorren ese último tramo. El 18308 alcanza el apeadero sin pasar por Peñaranda. Contrastar los pasos de cabecera con la vía representada, conservar las horas publicadas en Ávila y Salamanca, y estimar únicamente los pasos sin hora. Una sola identidad de viaje en las tres líneas, un paso por tramo y día. Verificar las salidas sin parada en Pinar y los servicios ya presentes en la 100 y en las LAV.
4. **Cierre entre estaciones.** Por decisión del 27/11, el cierre público de la 122 y del trayecto urbano se consulta en el comparador entre estaciones, como en Pinar. Comprobar que las fichas muestran el recuento del día y enlazan a los horarios comerciales de ambos extremos. Las pruebas de coincidencia por minutos, en ambos sentidos y en el acceso urbano, usan servicios y tramos ficticios con un control fuera de la ventana. [Método de simulación](../simulacion.md).
5. **Entrega de datos.** Crear la especificación y registrarla en `settings.py` y en `SPECS`. Actualizar asignaciones, conexiones, fuentes y pruebas de la 100, de la nueva línea y del enlace afectado. En una base vacía propia, validar la línea y la red, importar y exportar una vez con la base de integración definitiva. Justificar por conjunto y fecha los cambios de recuentos, pasos, destinos, histórico y análisis. Comprobar índice, fichas, comparador y simulación con pruebas de backend y Playwright, actualizar el inventario y la documentación y verificar el despliegue según AGENTS.md. [Procedimiento](../../.claude/skills/anadir-linea/SKILL.md) · [datos](../datos.md#añadir-otra-línea).

## Registro de fuentes

Las consultas y la lectura de las copias conservadas se hicieron el **26/11/2026**. Las cifras medidas, los IDs internos nuevos y los límites propuestos del grafo son resultados de esta investigación. Los siguientes originales permiten volver a contrastarlos.

| Editor y fuente | Qué respalda | Condiciones de uso |
|---|---|---|
| BOE, [catálogo de la RFIG][boe]. Adif, [DR 2026, tabla de clasificación][dr] y [portal de ediciones][portal] | Identidad, extremos, longitud de catálogo, ancho, electrificación y número de vías generales | Texto normativo público. DR de consulta pública, © Adif |
| Adif y Adif AV, [mapas RFIG 3 y 4, edición de 27/02/2026][mapas], en su [portal][portal] | Máxima de 155 en la diagonal Ávila–Salamanca, simbología de protección, bloqueo y mando | Consulta pública, © Adif y Adif AV |
| Adif, [esquemas de mantenimiento, lámina de Salamanca][esquema] y [relación de instalaciones 2026][instalaciones]. Ministerio de Transportes, [perfil longitudinal 122][perfil] | PK por eje, orden de las instalaciones, apeaderos y distinción con La Serna. El perfil histórico solo sirve de contraste físico | Consulta pública, sin licencia abierta identificada para reproducir mapas o perfiles |
| Adif, [Ávila][avila], [Salamanca][sal], [La Alamedilla][ala], [Vialia][vialia] y [energía de la 120][energia]. Junta de Castilla y León, [proyecto de Babilafuente][babilafuente] | Códigos e identidad de las terminales, estado de la electrificación vecina a la fecha de la noticia y ramal industrial | Páginas de consulta pública, © de sus editores |
| Colaboradores de OpenStreetMap, [R-20][r20], [relación por Ávila][r122] y [relación por Medina][r120] | Caminos entre IDs de nodo, longitudes medidas y etiquetas de vía. Las relaciones son de servicio | [ODbL 1.0 con atribución](https://www.openstreetmap.org/copyright) |
| Adif, [catálogo INSPIRE][inspire] | Objeto y alcance de la tramificación. No se usó como fuente de máximas operativas | Metadatos públicos. Para reutilizar geometría revisar las condiciones de la distribución concreta |
| Renfe Viajeros, [GTFS AV/LD/MD][gtfs], copias del 08, 12 y 17/11 | Paradas comerciales, números, productos, horas, calendarios y variantes | CC BY 4.0 |
| Ouigo / Ministerio de Transportes, [NAP](https://nap.transportes.gob.es/ConjuntoDato/Detail/1515). Compilación Iryo, [GTFS](https://clementdesouche.fr/gtfs). SNCF, [horarios abiertos](https://transport.data.gouv.fr/datasets/horaires-sncf) | Control de cobertura en los ficheros del 12, 18 y 26/11 respectivamente | Licencia de datos abiertos del Ministerio para Ouigo. CC BY 4.0 sobre la compilación de Iryo, horarios © Iryo. ODbL 1.0 para SNCF. [Registro de Oniel][fuentes] |
| Adif, [estado][estado], [avisos de viajeros][avisos], [panel fechado de Peñaranda][pen15] y [catálogo de restricciones, 26/11][rtc]. Renfe, [boletín del 17/11][huelga] y [pliego del 11–13/12][pat] | Localización y vigencia de incidencias, transporte alternativo y servicios afectados. Los paneles se actualizan | Consulta pública, © Adif / Renfe |
| Oniel, [base revisada][base], [reglas de la 100][conv] y [acceso de #315][enlace] | IDs preexistentes, recuentos de control en Pinar y reglas a conservar | Documentación y especificaciones del propio proyecto |

[base]: https://github.com/ebotiab/Oniel/tree/b0f3ad525963311334259fd8256be45d1f339671
[conv]: https://github.com/ebotiab/Oniel/blob/b0f3ad525963311334259fd8256be45d1f339671/backend/data/curated/madrid-avila-valladolid.json
[olmedo]: ../../backend/data/curated/lav-olmedo-ourense.json
[fuentes]: ../../backend/data/curated/sources.json
[pio]: https://github.com/ebotiab/Oniel/pull/315
[enlace]: https://github.com/ebotiab/Oniel/blob/df3c888c8e2495793359c623a17e95b023b17ba1/backend/data/curated/enlace-principe-pio-pinar.json
[conv315]: https://github.com/ebotiab/Oniel/blob/df3c888c8e2495793359c623a17e95b023b17ba1/backend/data/curated/madrid-avila-valladolid.json
[boe]: https://www.boe.es/buscar/act.php?id=BOE-A-2015-4382
[dr]: https://www.adif.es/documents/20124/45113726/20250613_01_DR_Adif_Libro_2026.pdf/b74bbb86-ddd0-bdf7-d976-18cab630f2df
[portal]: https://www.adif.es/sobre-adif/declaracion-red
[mapas]: ../../backend/data/raw/adif/dr-adif-av-2026-mapas_2026-11-12.pdf
[esquema]: https://contrataciondelestado.es/wps/wcm/connect/9cad6d4c-23da-4a50-98e3-29b24b7dcc58/001_0000652393_1403AmbitosTerritorialesPdf.PDF?MOD=AJPERES
[perfil]: https://cdn.transportes.gob.es/portal-web-transportes/ferroviario/organizacion_sector_ferroviario/innovacion/l-122_avila-salamanca.pdf
[instalaciones]: https://www.adif.es/documents/20124/37681091/20241210_04_DR_Adif_Relac.IISS_2026.pdf/e520cc0d-5820-e5fd-8593-21f1e130a477?download=true&version=1.0
[babilafuente]: https://participacyl.es/legislation/processes/2975/proposals
[avila]: https://www.adif.es/w/10400-%C3%A1vila
[sal]: https://www.adif.es/w/30100-salamanca
[ala]: https://www.adif.es/w/30110-salamanca-alamed.-
[vialia]: https://www.adif.es/w/salamanca
[energia]: https://www.adif.es/w/adif-mantenimiento-instalaciones-energia-linea-medina-salamanca-fuentes-o%C3%B1oro
[inspire]: https://datos.gob.es/es/catalogo/e0dat0002-red-de-transporte-ferroviario-de-adif1
[r20]: https://www.openstreetmap.org/relation/1210118
[r122]: https://www.openstreetmap.org/relation/6016263
[r120]: https://www.openstreetmap.org/relation/6016262
[gtfs]: https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia
[estado]: https://www.adif.es/viajeros/estado-de-la-red
[avisos]: https://www.adif.es/viajeros/avisos
[rtc]: https://www.adif.es/documents/d/adif/20261126_07_adif_2026_rtc
[pen15]: https://www.adif.es/w/34010-pe%C3%B1aranda-bracam.
[huelga]: https://grupo.renfe.com/content/dam/grupo-renfe/sala-de-prensa/sala-de-prensa/general/pdf-y-otros/Trenes%2017%20de%20noviembre%20OSP.pdf
[pat]: https://contrataciondelestado.es/FileSystem/servlet/GetDocumentByIdServlet?DocumentIdParam=FGZgIKcEmsxeP3OxWOyc1cgyxX9GZFeFQVRnHnOr8E28yrk%2FcSz5UfweobIu5fKmtptQyOBXwjMSO3UznbCa3TygeC%2FwuONVtXZJVDuGfGgC1%2FzDIE0Kw%2FPWNnLS0Z0z&cifrado=QUC1GjXXSiLkydRHJBmbpw%3D%3D
