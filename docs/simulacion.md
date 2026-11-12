# Simulación de cierre de un tramo

La simulación responde a una pregunta sencilla: **si este tramo se cerrase tal día entre tal hora y tal otra, ¿qué trenes se verían afectados?** Es una herramienta secundaria del visor; el objetivo principal de Oniel es entender cómo está conectada la red.

## Qué datos usa

- La red cargada: nodos (estaciones, PAET, PB, bifurcaciones, cambiadores) con su kilómetro en cada línea y tramos entre nodos consecutivos.
- Los horarios publicados por Renfe en su GTFS (`backend/data/raw/renfe/`): para cada tren, sus paradas con hora de llegada y salida.
- Una asignación curada de cada parada GTFS a la red, por línea (`stop_mappings` en `backend/data/curated/<línea>.json`): o la parada es un nodo de la línea, o está fuera y el tren entra o sale de la línea por un nodo concreto (por ejemplo, Málaga sale de la LAV por la bifurcación de Málaga; Jaén sale de la línea convencional por Espelúy).
- Las reglas de recorrido (`route_overrides`) para los trenes que cambian de línea a mitad de camino: dicen entre qué paradas el viaje va por cada línea y por qué nodo sale hacia las otras.
- Las interrupciones del servicio registradas a mano (`backend/data/curated/anotaciones.json`, descritas en `docs/datos.md`): no cambian el cálculo, pero el resultado dice cuándo el tramo o su alternativa ya están interrumpidos en la fecha simulada.

## Cómo se calcula el paso de un tren por un tramo

Está implementado en `backend/src/oniel/sim/passes.py` y se precalcula en la importación, línea a línea.

1. **Publicado.** Si el tren para en las dos estaciones que delimitan el tramo, entra a la hora de salida de la primera y sale a la hora de llegada de la segunda. Sin margen.
2. **Estimado.** Si no para en uno de los extremos, repartimos el tiempo entre sus dos paradas publicadas en proporción a la distancia recorrida por la línea. Margen de incertidumbre: 15 % del tiempo entre esas paradas, con un mínimo de 3 minutos. El extremo que sí coincide con una parada mantiene su hora publicada sin margen.
3. **Estimado con una parada fuera de la red.** Si una de las paradas está fuera de la línea cargada, el reparto usa la distancia por la línea hasta el nodo de salida más la distancia en línea recta desde ese nodo hasta la parada exterior. Margen: 30 %, mínimo 5 minutos.
4. **Estimado con una parada en otra línea cargada.** Un tren que cambia de línea se resuelve en cada una solo entre las paradas que le corresponden, según su regla de recorrido. En la línea que deja, la primera parada de la otra línea es una salida, y su asignación dice por dónde se llega a ella (`via`): la línea y el nodo por el que el tren entra. La distancia desde la salida hasta esa parada se mide entonces por esa línea, no en línea recta; solo si la salida y el nodo de enlace son puntos distintos se añade la línea recta entre los dos. Margen: 30 %, mínimo 5 minutos, y la explicación del paso dice en qué línea está la parada y por dónde sale o entra el tren.
5. **Estimado a través de varias líneas.** Un viaje puede recorrer tres líneas o más. El modelo sigue resolviéndolo línea a línea; lo que cambia es que el camino hasta una parada puede cruzar más de una línea, y entonces `via` es una lista de trechos: cada uno entra en su línea por un nodo y la deja en el nodo del trecho siguiente, que tiene que ser común a las dos, y el último llega a la parada. La distancia es la suma de los kilómetros de cada trecho por su línea. Si el tren cruza una línea entera sin parar en ella, sus dos paradas quedan fuera, una a cada lado; cuando a las dos se llega por líneas cargadas, el recorrido está fijado (entra por un nodo y sale por otro) y el paso es estimado. También lo está cuando solo a una se llega por una línea cargada y la otra queda fuera de la red, con coordenadas para medir la línea recta hasta ella: es el caso de los trenes de Córdoba a Málaga que recorren sin parar la línea hasta Antequera-Santa Ana. Margen: 30 % del mayor de los dos tiempos que el tren pasa fuera de la línea (de la parada anterior a la entrada, o de la salida a la parada siguiente), mínimo 5 minutos; es el margen que las líneas vecinas dan a esos mismos puntos de enlace.
6. **Indeterminado.** Si el horario incluye una parada que no sabemos situar, o las dos paradas de un trayecto están fuera de la línea y a ninguna se llega por una línea cargada, no podemos fijar el recorrido: el paso queda indeterminado.

## Cómo se decide si un tren está afectado

Está en `backend/src/oniel/sim/closure.py`. Para cada tren que recorre el tramo el día elegido (y los del día anterior que terminan después de medianoche) comparamos la ventana con su intervalo de paso:

- Si ni siquiera con los márgenes se tocan → **no afectado**.
- Si se solapan aun descontando los márgenes → **afectado** (publicado o estimado, según el origen del dato).
- Si solo se tocan dentro del margen de incertidumbre, o el paso era indeterminado → **indeterminado**.

Las ventanas que terminan antes de empezar (23:00 a 01:00) se interpretan como que acaban al día siguiente.

## Recorrido alternativo

Desde que Oniel carga líneas que comparten nodos (Madrid-Puerta de Atocha y Córdoba, la alta velocidad y la convencional; Manzanares y Ciudad Real, la tercera con cada una de las otras), el resultado de un cierre dice también si **existe otro recorrido cargado** que salve el tramo. El cálculo sale del grafo de rutas (véase «Grafo y escenarios»): el cierre es un escenario de una modificación, y `oniel.sim.closure.alternatives` pide al grafo los rodeos que lo salvan.

Un rodeo sale de la línea del tramo cerrado por un nodo situado antes del cierre, sigue por otras líneas, una sola o varias encadenadas, y vuelve a la línea por un nodo situado después. No usa ningún tramo de la línea cerrada ni pasa por sus nodos intermedios, así que cada rodeo es el más ceñido al tramo de los que siguen su camino. De cada uno se informa de los kilómetros por cada línea y en total, de los kilómetros entre los mismos dos nodos por la línea cerrada, de las estaciones principales intermedias, de los kilómetros de vía única y del tiempo estimado. Van del más corto al más largo.

Ejemplos:

- Cierre de Urda – Ciudad Real (LAV): dos alternativas. La más corta es la que siguen los Intercity y Alvia desviados tras la interrupción de la alta velocidad: por la convencional hasta Manzanares y por la línea de Manzanares a Ciudad Real, 260,5 km frente a 170,8 km por la alta velocidad, con 64,4 km de vía única. La otra es la convencional entera entre Madrid-Puerta de Atocha y Córdoba.
- Cierre de Villanueva de Córdoba – Adamuz (LAV): por la línea convencional entre Madrid-Puerta de Atocha y Córdoba, 440,7 km por Aranjuez, Alcázar de San Juan, Manzanares, Valdepeñas, Santa Cruz de Mudela, Vilches, Linares-Baeza y Andújar frente a 343,6 km por la alta velocidad, con 194,1 km de vía única. Y, más ceñido al tramo, de Ciudad Real a Córdoba por Manzanares: 309,0 km por dos líneas frente a 172,8 km.
- Cierre de Venta de Cárdenas – Vilches (convencional, Despeñaperros): por la LAV entre Madrid-Puerta de Atocha y Córdoba, 343,6 km frente a 440,7 km. Y de Manzanares a Córdoba por Ciudad Real y la alta velocidad, 237,2 km frente a 244,6 km.
- Cierre de Almagro – Ciudad Real (línea de Manzanares a Ciudad Real): ninguna línea sola tiene un nodo a cada lado del tramo; el rodeo encadena dos, la convencional hasta Madrid y la alta velocidad hasta Ciudad Real (366,9 km frente a 64,4 km), o la convencional hasta Córdoba y la alta velocidad de vuelta (417,4 km).
- Cierre de Bifurcación Málaga – Majarabique (LAV): sin alternativa cargada, porque al sur de Córdoba Oniel solo tiene una línea.

Las alternativas por una sola línea son las mismas que antes de pasar por el grafo, con los mismos nodos, kilómetros y texto: se comprobó en los 39 tramos, en dos fechas, contra el cálculo anterior (`network_repo.fetch_alternatives`, ya retirado). Lo nuevo son los rodeos por varias líneas.

Lo que **no** hace la simulación, y haría falta para un desvío real:

1. Decidir qué trenes afectados podrían tomar la alternativa. Depende del material (un AVE de ancho estándar no puede circular por la red convencional de ancho ibérico; un Alvia o un Intercity de ancho variable sí, cambiando de ancho en un cambiador que hoy no está modelado como requisito) y de si el tren tiene paradas intermedias que la alternativa no sirve. El grafo tampoco lo sabe: une alta velocidad y convencional en los nodos comunes sin mirar el ancho de vía.
2. Estimar el nuevo horario: el tiempo del recorrido alternativo es una estimación sin paradas (véase «Grafo y escenarios»), y faltan los huecos en la ocupación de la vía única, donde los cruces limitan cuántos trenes caben por hora en cada sentido.
3. Deducir por sí sola el recorrido de un tren que cambia de línea: hoy hay que declararlo en una regla de recorrido de cada especificación, como se hizo con los Intercity y Alvia Madrid-Atocha Cercanías–Andalucía (véase `docs/datos.md`).
4. Descontar los trenes que en realidad no circulan. La simulación señala que el tramo o la alternativa tienen una interrupción real registrada ese día (véase «Interrupciones reales»), pero sigue comparando la ventana con el horario publicado.

## Grafo y escenarios

La simulación de cierre, el recorrido alternativo y el comparador de recorridos de la hoja de ruta hacen la misma pregunta: con la red así, ¿por dónde se va de un nodo a otro y cuánto cuesta? La responde un solo cálculo, `backend/src/oniel/routing/`, que no toca la base de datos.

**El grafo.** Los nodos son los de la red y las aristas, los tramos de todas las líneas cargadas. Un nodo común a dos líneas es uno solo, con su kilómetro en cada una: por ahí se cambia de línea. `network_repo.fetch_graph` lo construye con las mismas lecturas que `GET /api/network`.

**El escenario.** Es una lista de modificaciones sobre la red, no una copia de ella:

- cerrar un tramo;
- añadir un enlace esbozado entre dos nodos, con su longitud y su velocidad (un proyecto que aún no existe, por ejemplo);
- cambiar la velocidad de un tramo.

Se guarda como JSON (`{"closures": [...], "links": [...], "speeds": [...]}`) y como una cadena corta para la URL, que une las modificaciones con `;` y sus campos con `~`: `c~<tramo>`, `e~<nodo>~<nodo>~<km>~<km/h>` y `v~<tramo>~<km/h>`. Por ejemplo, `c~lav-madrid-sevilla:urda:ciudad-real` cierra Urda – Ciudad Real. Un tramo o un nodo que no existe en la red hace el escenario inválido. Las interrupciones vigentes un día pueden sumarse como cierres (`Scenario.with_closures`), pero solo si se pide: por defecto se señalan y no se aplican.

**Los recorridos.** `find_routes` devuelve los caminos entre dos nodos que no pasan dos veces por el mismo nodo, del más corto al más largo, con un tope de doce. No los limita por el número de líneas que encadenan: lo que descarta un recorrido es que dé un rodeo desproporcionado (`max_ratio`, 2 por defecto). Se compara con cada recorrido más corto que ya está en la lista: se quitan los tramos que los dos comparten al principio y al final, y si la parte propia del largo mide más del doble que la del corto, se descarta. Cuando no comparten ningún tramo, es la comparación de las dos longitudes enteras. La regla da lo mismo en los dos sentidos. Así, Madrid – Córdoba tiene cuatro recorridos (alta velocidad, 343,6 km; convencional hasta Manzanares, línea de Manzanares a Ciudad Real y alta velocidad, 433,3 km por tres líneas, que es el de los Alvia desviados que no paran en Ciudad Real; convencional entera, 440,7 km; y alta velocidad hasta Ciudad Real, vuelta a Manzanares y convencional, 479,8 km) y Madrid – Ciudad Real, dos (alta velocidad, 170,8 km; convencional hasta Manzanares y línea de Manzanares a Ciudad Real, 260,5 km). La vuelta por Córdoba, 613,5 km, mide 3,6 veces lo que el más corto y se descarta. De Sevilla a Manzanares se descarta el camino que llega a Ciudad Real y sube hasta Madrid para volver: mide 666,4 km frente a 363,9 km, menos del doble, pero desde Ciudad Real recorre 366,9 km para lo que el más corto hace en 64,4 km.

Hasta la PR del comparador el criterio era otro: un solo paso de una línea a otra (`max_changes=1`). Se cambió con la lista real delante, porque dejaba fuera el recorrido de los Alvia desviados (tres líneas) y dejaba pasar la vuelta por Córdoba. `max_changes` sigue existiendo como freno técnico, con cinco pasos por defecto (seis líneas encadenadas): la búsqueda recorre todos los caminos simples, y con muchas más líneas cargadas habrá que podarla por longitud en vez de enumerarlos todos. La proporción se mide contra el más corto de los que quedan en el escenario: con Urda – Ciudad Real cerrado, Madrid – Ciudad Real tiene un solo recorrido, el de 260,5 km.

Cada recorrido lleva:

- **Kilómetros.** Por cada línea, la diferencia entre los kilómetros del nodo de entrada y el de salida; un enlace esbozado aporta los suyos. El total es la suma de los trechos.
- **Tiempo estimado.** La suma, tramo a tramo, de su longitud entre su velocidad habitual (`typical_speed_kmh`; la máxima si no hay habitual), en minutos enteros. Es el tiempo de recorrer cada tramo a esa velocidad sin parar, sin acelerar ni frenar y sin esperar cruces en vía única: sirve para comparar recorridos entre sí, no es un horario. Madrid – Ciudad Real sale en 40 minutos por la alta velocidad y en 107 por Manzanares; los Intercity desviados tardan 155 minutos publicados en ese mismo recorrido. Si a algún tramo le falta la velocidad, el recorrido no lleva tiempo.
- **Kilómetros de vía única**, las **líneas usadas** en orden, un **trecho** por cada línea (con sus nodos, kilómetros, tiempo y vía única) y las **estaciones principales** intermedias en el orden en que se recorren.

**La API.** `GET /api/routes?from=<nodo>&to=<nodo>` devuelve los recorridos y el método. Admite `scenario` (la cadena corta o el JSON), `max_changes`, `max_ratio`, `date` (cada recorrido lleva entonces las interrupciones vigentes ese día en sus tramos) y `avoid_interruptions=true` (con fecha, los tramos interrumpidos se cierran además). `POST /api/simulations/closure` acepta también `scenario`: el cierre del tramo se suma a sus otras modificaciones al buscar la alternativa.

**El visor.** `frontend/src/routing/` hace el mismo cálculo en el cliente sobre la red que compone el visor a partir del índice (`index.json`, que lleva todas las líneas, nodos y tramos), para que el modo estático no dependa de la API; su interfaz es el comparador de recorridos (véase «Comparar recorridos»). La ruta `#/escenario/<cadena>` abre un escenario: hoy, si cierra un tramo, abre la simulación de ese cierre y la URL lo conserva.

**Paridad.** Servidor y cliente tienen que dar lo mismo. `backend/tests/test_routing.py` resuelve diez casos sobre la instantánea y los compara con `frontend/e2e/fixtures/rutas-paridad.json`; `frontend/e2e/rutas.spec.ts` resuelve los mismos casos en el cliente contra el mismo fichero y, con la API arrancada, compara además con `GET /api/routes`. Si el cálculo cambia a propósito, el fichero se regenera con `ONIEL_UPDATE_FIXTURES=1 uv run pytest tests/test_routing.py`. Los redondeos usan la misma fórmula en los dos lados.

Límites: el grafo no distingue anchos de vía ni sentidos, no sabe por qué vía de una estación se pasa de una línea a otra y trata un cambio de línea como instantáneo.

## Comparar recorridos

El comparador del visor (`#/recorridos/<desde>/<hasta>`) responde a «¿cómo se va de una estación a otra y qué diferencia hay entre un camino y otro?». Calcula en el cliente, con el grafo de `frontend/src/routing/`, así que funciona igual sin API; lo que decide cómo se presentan los recorridos está en `frontend/src/app/recorridos.ts`.

**Qué recorridos enseña.** Los tres primeros de `find_routes` con su criterio por defecto: sin tope útil de líneas, descartados los que dan un rodeo de más del doble respecto a otro más corto, del más corto al más largo. Tres bastan para los casos que hoy tienen sentido y dejan fuera los zigzags. La lista real con las líneas cargadas (la última fila, desde que están las dos de alta velocidad de Córdoba a Granada; el camino convencional a Granada por Linares-Baeza y Moreda aún no está cargado, así que los tres recorridos llegan por Antequera):

| Par | Se enseñan | Quedan fuera |
|---|---|---|
| Madrid – Córdoba | 343,6 km (alta velocidad), 433,3 km (por Manzanares y Ciudad Real, tres líneas), 440,7 km (convencional, 194,1 km de vía única) | 479,8 km (el cuarto) |
| Madrid – Ciudad Real | 170,8 km (alta velocidad), 260,5 km (por Manzanares, 64,4 km de vía única) | 613,5 km (por Córdoba, más del doble) |
| Madrid – Andújar | 361,9 km (convencional), 401,0 km (por Ciudad Real y Manzanares), 422,4 km (por Córdoba) | 512,1 km (el cuarto, por cuatro trechos) |
| Manzanares – Ciudad Real | 64,4 km | 366,9 km y 417,4 km (más del doble) |
| Madrid – Granada | 569,0 km (alta velocidad por Córdoba y Antequera, tres líneas, 81,0 km de vía única, 138 minutos estimados), 658,8 km (convencional hasta Manzanares, Ciudad Real y alta velocidad desde allí) y 666,1 km (convencional hasta Córdoba y alta velocidad desde allí) | 705,2 km (el cuarto) |
| Sevilla – Manzanares | 363,9 km (por Ciudad Real), 371,2 km (por Córdoba y la línea convencional) | 666,4 km (sube de Ciudad Real a Madrid y vuelve) |

El detalle dice cuántos quedan fuera por ser el cuarto o posteriores; los descartados por largos no se cuentan.

**Recorridos cortados.** Las interrupciones vigentes hoy y los cierres de un escenario no quitan recorridos de la lista: los señalan, para que se vea cuál se pierde y cuál queda. Si el más corto está cortado, el primero que no lo está se marca como «el más corto que no está cortado». Si todos los que se enseñan están cortados, se busca además el más corto con esos tramos cerrados, mida lo que mida, y se añade a la lista (Manzanares – Ciudad Real con un tramo cerrado: 366,9 km por Madrid). Si no existe, se dice. El 11 de noviembre de 2026, con la alta velocidad interrumpida entre la Bifurcación La Sagra y Córdoba y la convencional entre Almuradiel-Viso del Marqués y Alcolea de Córdoba, los tres recorridos entre Madrid y Córdoba están cortados y no hay otro; entre Madrid y Ciudad Real, el de la alta velocidad está cortado y el de Manzanares queda como alternativa.

**Escenario.** La ruta admite un escenario detrás de las estaciones (`#/recorridos/madrid-puerta-de-atocha/ciudad-real/c~lav-madrid-sevilla:urda:ciudad-real`). Sus enlaces esbozados y sus cambios de velocidad cambian la red; sus cierres se tratan como cortes. Un escenario que no encaja con la red se ignora y el panel lo dice. Todavía no hay un conmutador de enlaces hipotéticos, porque no hay proyectos con trazado cargados (#18): cuando los haya, cada uno será un escenario que se añade a esta ruta. Un enlace esbozado no se dibuja en el mapa.

**Trenes directos.** Son los servicios que paran en las dos estaciones, en ese sentido, el día de referencia de los horarios (las paradas de cada nodo: `nodes/<id>.json` o `GET /api/nodes/{id}/services`), siempre que en la primera se pueda subir y en la segunda bajar: algunos trenes solo dejan o solo recogen viajeros en una parada (de Ciudad Real a Madrid pasan 23 y sirven 12). Es el mismo criterio y el mismo número que los destinos directos de la ficha de cada estación (`docs/datos.md`, «Destinos directos»). El tiempo del más rápido es el publicado, de la salida de una a la llegada a la otra. Un tren se asigna a un recorrido cuando pasa por el primer y el último tramo de cada línea que el recorrido encadena (los pasos de cada tramo: `segments/<id>.json` o `GET /api/segments/{id}/services`). El 13 de noviembre de 2026 hay 55 directos de Madrid a Córdoba, 6 de ellos de Ouigo: 43 por la alta velocidad (el más rápido, 1 h 44 min, frente a 1 h 21 min estimados sin paradas) y 12 por Manzanares y Ciudad Real (3 h 45 min, frente a 2 h 28 min). Son trenes del horario publicado: si el recorrido está cortado, la línea roja de la ficha lo dice.

**Lo que el comparador dice de sus límites**, a la vista y no en el detalle:

1. El tiempo es longitud entre velocidad habitual, tramo a tramo, sin paradas, sin acelerar ni frenar y sin esperar cruces en vía única. Sirve para comparar recorridos, no es un horario.
2. El grafo no distingue anchos de vía: une la alta velocidad (ancho estándar) y la red convencional (ancho ibérico) en los nodos comunes como si cualquier tren pudiera pasar. Solo pueden los de ancho variable, por un cambiador que Oniel no modela como requisito.

Está automatizado en `frontend/e2e/recorridos.spec.ts` (el criterio, los cortes, la URL, los tiempos y la vista con Madrid – Córdoba y Madrid – Ciudad Real, también en modo estático) y, para el cálculo, en `backend/tests/test_routing.py`.

## Tramos sin alternativa

Para cada tramo, Oniel dice cuántos trenes lo recorren un día y si, con el tramo cortado, esos trenes tendrían otro camino. Lo calcula el servidor (`backend/src/oniel/analysis/criticality.py`) con dos cosas que ya existían: los pasos de cada tren por cada tramo y el grafo de rutas. No añade ningún dato externo.

**«Sin alternativa» significa siempre «en las líneas que Oniel tiene cargadas».** Al sur de Córdoba Oniel tiene una sola línea, así que sus tres tramos salen sin alternativa aunque en la red real haya otras vías. El resultado lleva ese aviso como texto (`scope_note`), la lista de líneas en las que se ha buscado (`line_ids`) y los operadores cuyos trenes no están contados (`missing_operator_ids`; hoy, Iryo), y el visor lo dice junto a cada cifra.

**Cómo se calcula.**

1. De cada tren del día se toman los tramos cargados que recorre (`services_repo.service_paths`; son los mismos pasos que cuentan los recuentos por tramo y por operador).
2. Para un tramo, el **recorrido** de cada tren es el trozo seguido de esos tramos que contiene al que se mira, del nodo por el que el tren entra en las líneas cargadas al nodo por el que sale (`corridor`). Un AVE de Madrid a Málaga entra por Madrid-Puerta de Atocha y sale por la Bifurcación Málaga-Alta Velocidad; un tren de Madrid a Jaén, por Espelúy. Si los tramos de un tren no forman un camino sin bifurcaciones, su recorrido se queda en el propio tramo.
3. Los trenes con el mismo recorrido forman un **grupo**: comparten extremos y camino, así que comparten respuesta.
4. Con el tramo cerrado (un escenario de un cierre), `find_routes` busca los caminos entre los dos extremos del grupo, sin descartar ninguno por largo. Si hay alguno, el más corto es **el otro camino**, y se compara con el recorrido del tren medido con la misma vara (`route_along`): kilómetros por cada línea y minutos a la velocidad habitual de cada tramo, sin paradas. Si no hay ninguno, el grupo no tiene alternativa.

Cada tramo se cierra por separado sobre la red completa: las interrupciones vigentes no se aplican. Hoy, con la alta velocidad y la convencional interrumpidas a la vez, varios de los «otros caminos» están también cortados; el comparador de recorridos es el que cruza cortes reales con caminos.

**Lo que sale** con los trenes del 13 de noviembre de 2026 (229 trenes, 39 tramos):

| Tramos | Trenes al día | Otro camino en las líneas cargadas |
|---|---|---|
| Córdoba – Bifurcación Málaga (LAV) | 108 | Ninguno |
| Bifurcación Málaga – Majarabique (LAV) | 55 | Ninguno |
| Majarabique – Sevilla-Santa Justa (LAV) | 53 | Ninguno |
| Ciudad Real – Córdoba (LAV, cuatro tramos) | 108 | Para los 43 de Madrid a Sevilla, la línea convencional hasta Córdoba: 97 km y 1 h 44 min más. Para los 24 desviados por Manzanares, 7 km y 38 min más |
| Madrid – Ciudad Real (LAV, cuatro tramos) | 84 | Por la convencional hasta Manzanares y la línea de Manzanares a Ciudad Real: 90 km y 1 h 6 min más |
| Manzanares – Ciudad Real (tres tramos) | 38 | Para los 24 desviados, la alta velocidad directa: 90 km y 1 h 6 min menos |
| Manzanares – Linares-Baeza (convencional) | 18 a 26 | Para los 16 de Madrid a Espelúy, por la alta velocidad hasta Córdoba y de vuelta: 105 km más y 29 min menos |

Los 36 tramos al norte de Córdoba tienen otro camino para todos sus trenes. Que el otro camino salga más corto o más rápido no es un error: los trenes desviados tras la interrupción de la alta velocidad ya dan un rodeo, y el tiempo estimado de la alta velocidad es menor aunque recorra más kilómetros.

**La API y la instantánea.** `GET /api/alternatives` (con `?date=` para otro día) devuelve un elemento por tramo: trenes, reparto por operador, cuántos tienen otro camino y cuántos no, y los grupos, del más numeroso al menos, cada uno con sus extremos, lo que mide y tarda su recorrido y, si existe, el otro camino (kilómetros, minutos, diferencia con el recorrido, vía única, líneas y estaciones principales). La instantánea lo lleva en `alternatives.json`, que el visor no pide al arrancar (`docs/datos.md`, «Instantánea estática»). Si la API no tiene la ruta o falla, el visor lee ese fichero: Vercel publica el visor unos minutos antes de que Render despliegue la API, y en ese rato una ruta nueva da 404. El cliente no repite el cálculo: necesitaría los tramos de todos los trenes del día.

**En el visor.** La ficha del tramo lo dice en una frase bajo «Trenes que lo recorren» y desglosa los grupos en «Más detalle»; el panel «Cobertura y fuentes» lista los tramos sin alternativa, del que más trenes lleva al que menos, y pliega los demás (`docs/diseno.md`, «Tramos sin alternativa»). Las frases están en `frontend/src/app/alternativas.ts`.

**Qué no mide.**

1. Nada fuera de las líneas cargadas. Un tramo «sin alternativa» puede tenerla en la red real, y uno «con alternativa» puede tener otra mejor que Oniel no conoce.
2. Si el tren puede tomar el otro camino. El grafo no distingue anchos de vía ni electrificación, y no mira las paradas que el tren dejaría de hacer.
3. La capacidad de la vía. No se modela cuántos trenes caben por el otro camino, ni los cruces en vía única; que 84 trenes «tengan otro camino» por una línea de vía única no quiere decir que quepan.
4. Los trenes que faltan: los de Iryo, Cercanías y mercancías. La carga real de cada tramo es mayor.
5. Los viajeros. Cuenta trenes, no plazas ni personas, y un tren que recorre varios tramos cuenta en cada uno.
6. El viaje fuera de las líneas cargadas. Los extremos de un grupo son por donde el tren entra y sale de ellas, no su origen y su destino.

Está automatizado en `backend/tests/test_criticality.py` (la convencional como alternativa de la alta velocidad entre Madrid y Córdoba, los tramos al sur de Córdoba, los grupos de trenes desviados y los recuentos de la instantánea), en `backend/tests/test_integration_db.py` (la API contra los recuentos por tramo) y en `frontend/e2e/alternativas.spec.ts` (la ficha y el panel, también en modo estático).

## Interrupciones reales

Un cierre simulado puede caer sobre un tramo que ya está interrumpido de verdad. La simulación no lo oculta ni lo corrige: lo dice.

- **En la vista de un tramo.** `GET /api/segments/{id}/services` devuelve, junto a los pasos del día, las interrupciones vigentes ese día en el tramo (`interruptions`). Cada una lleva su nota: «Horario publicado; sin circulación real desde el 6 de septiembre de 2026 (Adif).» El visor la muestra en una línea sobre la lista de trenes.
- **En el tramo que se cierra.** El resultado de `POST /api/simulations/closure` lleva en `interruptions` las vigentes en ese tramo en la fecha simulada y añade una advertencia al método: los trenes de la lista figuran en el horario, pero no circulan. El recuento de afectados no cambia.
- **En el recorrido alternativo.** Cada alternativa lleva en `interruptions` las vigentes ese día en algún tramo de su recorrido, y su nota termina diciendo entre qué nodos no hay circulación, desde cuándo y según quién. El 10 de noviembre de 2026, un cierre en la alta velocidad entre Madrid y Córdoba señala la alternativa por Despeñaperros y avisa de que está cortada entre Almuradiel-Viso del Marqués y Alcolea de Córdoba; un cierre en la convencional señala la alta velocidad y avisa de que está cortada entre la Bifurcación La Sagra y Córdoba. El rodeo de Madrid a Ciudad Real por Manzanares queda al norte del corte por obras y no lleva aviso.

Vale la fecha simulada, no la de hoy: un cierre simulado en una fecha anterior al inicio de una interrupción, o posterior a su final, no lleva ninguna nota. Está automatizado en `backend/tests/test_integration_db.py` y `frontend/e2e/interrupciones.spec.ts`.

## Trenes que recorren varias líneas

Los horarios de Renfe del 8 al 15 de noviembre de 2026 incluyen 24 Intercity y Alvia entre Madrid-Atocha Cercanías y Sevilla, Málaga, Ronda o Algeciras que tardan 2 h 50 entre Madrid y Ciudad Real y 1 h 15 entre Ciudad Real y Córdoba: el desvío por la red convencional que aparece en los horarios tras la interrupción de la alta velocidad en Urda. Según esos horarios, van por la convencional hasta Manzanares, por la línea de Manzanares a Ciudad Real y, desde Ciudad Real, por la alta velocidad; la interrupción registrada de la alta velocidad incluye Ciudad Real – Córdoba, y Oniel no sabe si circulan (`docs/datos.md`, «Interrupciones registradas»). Cada una de las tres líneas los declara en `route_overrides`, y el resultado es el siguiente, tomando el Intercity 10270 (Madrid-Atocha Cercanías 6:00 → Ciudad Real 8:35/8:50 → Córdoba 9:45/9:50 → Sevilla 10:53) del viernes 13 de noviembre de 2026:

| Punto | Distancia desde Madrid | Tiempo proporcional | Hora |
|---|---|---|---|
| Manzanares (fin de la convencional, km 196,1) | 196,1 km | 155 × 196,1 / 260,5 = 116,7 min | 7:56:40 |
| Daimiel (km 21,4 de la tercera línea) | 217,5 km | 155 × 217,5 / 260,5 = 129,4 min | 8:09:25 |
| Almagro (km 42,7) | 238,8 km | 155 × 238,8 / 260,5 = 142,1 min | 8:22:06 |
| Ciudad Real (km 64,4) | 260,5 km | 155 min | 8:35:00, publicada |

- En la línea convencional se resuelve entre Madrid y Ciudad Real, saliendo por Manzanares: las 2 h 35 se reparten entre 196,1 km por esa línea y 64,4 km por la de Manzanares a Ciudad Real. Pasos estimados en los once tramos Madrid–Manzanares (sale de Manzanares hacia las 7:56, margen de ±35 min) y ninguno más allá. Su explicación dice: «usa 196 km por la línea y, desde Manzanares, 64 km por esa línea hasta Ciudad Real».
- En la línea de Manzanares a Ciudad Real se resuelve entre las mismas dos paradas, entrando por Manzanares: pasos estimados en sus tres tramos, a las horas de la tabla, con margen de ±11 min (30 % de los 38 minutos que pasa en la línea) salvo la llegada a Ciudad Real, que es la publicada. El tren no para en Daimiel ni en Almagro.
- En la LAV se resuelve desde Ciudad Real: paso publicado o estimado en Ciudad Real–Córdoba y Córdoba–Sevilla, y ninguno entre Madrid y Ciudad Real (ni en Urda–Ciudad Real).

Antes de cargar la tercera línea, los 64,4 km entre Manzanares y Ciudad Real se medían como 47 km en línea recta: la salida estimada de Manzanares era hacia las 8:05 y la explicación lo decía. Con la línea cargada el reparto usa la distancia real y el tren aparece en «Trenes que lo recorren» de Manzanares–Daimiel, Daimiel–Almagro y Almagro–Ciudad Real.

Los 4 Alvia que no paran en Ciudad Real (Madrid–Córdoba en 3 h 45, el mismo tiempo que los anteriores) reparten ese tiempo entre las tres líneas: 196,1 km por la convencional, 64,4 km por la de Manzanares a Ciudad Real y 172,8 km por la alta velocidad, 433,3 km en total. En la convencional, Córdoba es para ellos una salida por Manzanares, y el camino hasta ella cruza las otras dos líneas; en la LAV, Madrid-Atocha Cercanías es una entrada por Ciudad Real, con el camino inverso; y la línea de Manzanares a Ciudad Real la cruzan sin parar, entre una parada de la convencional y otra de la alta velocidad. Las tres líneas reparten el mismo tiempo con la misma distancia total, así que las horas encajan en los enlaces: el Alvia 09366 de las 6:00 sale de la convencional en Manzanares hacia las 7:41 y entra en la alta velocidad en Ciudad Real hacia las 8:15. En la línea que cruza, el margen es de ±30 min: el 30 % de los 102 minutos que hay desde la salida publicada de Madrid hasta Manzanares.

Simulación de un cierre de Almagro – Ciudad Real el 13 de noviembre de 2026 de 8:00 a 9:00 (resultado de la API el 10 de noviembre de 2026): 38 trenes recorren el tramo ese día; 5 afectados (un MD con horario publicado y, con paso estimado, los Intercity 10270 y 10182 y los dos Alvia 09366), 2 indeterminados y 31 no afectados.

Está automatizado en `backend/tests/test_route_overrides.py`, `backend/tests/test_sim_passes.py` (el tren que cruza una línea sin parar), `backend/tests/test_integration_db.py` y `frontend/e2e/simulacion.spec.ts`.

## Caso comprobado a mano

Tramo **Villanueva de Córdoba – Adamuz** (km 285,2 a 317,8), viernes **13 de noviembre de 2026**, cierre de **8:00 a 9:00**.

El AVE 02070 (Madrid-Puerta de Atocha 7:00 → Sevilla-Santa Justa 9:48) para en Puertollano (salida 8:11) y en Córdoba (llegada 8:53): 42 minutos para 133,8 km. No para ni en Villanueva ni en Adamuz, así que su paso es estimado:

| Punto | Distancia desde Puertollano | Tiempo proporcional | Hora |
|---|---|---|---|
| Villanueva de Córdoba (km 285,2) | 75,4 km | 42 × 75,4 / 133,8 = 23,7 min | 8:34:40 |
| Adamuz (km 317,8) | 108,0 km | 42 × 108,0 / 133,8 = 33,9 min | 8:44:54 |

Margen: 15 % de 42 min = 6,3 min. Incluso descontando el margen (8:41 a 8:38, intervalo degenerado → punto medio 8:39:47) el paso cae dentro de 8:00–9:00, así que el resultado es **afectado (estimado)**, con paso de 08:34 a 08:44.

El mismo caso está automatizado en:

- `backend/tests/test_sim_passes.py::test_estimated_pass_is_proportional_to_distance`
- `backend/tests/test_sim_closure.py::test_hand_calculated_case_ave_02070`
- `backend/tests/test_integration_db.py::test_closure_hand_case` (contra la base de datos y la API, incluidas las alternativas)
- `frontend/e2e/simulacion.spec.ts` (desde la interfaz)

Resultado completo de la API para ese caso (8 de noviembre de 2026): 96 trenes recorren el tramo ese día; 6 afectados con paso estimado, 5 indeterminados, 85 no afectados.

## Limitaciones conocidas

- Los horarios son los planificados por Renfe y por Ouigo. Las interrupciones registradas en `anotaciones.json` (hoy, la de la alta velocidad desde el 28 de octubre de 2026 y la de la línea convencional por obras desde el 6 de septiembre de 2026) se señalan con una nota, pero sus trenes siguen en las listas y en los recuentos; las alteraciones que Oniel no tiene registradas no se señalan.
- Hay servicios de Renfe y de Ouigo. Faltan los de Iryo, que no publica sus horarios en un formato abierto, además de Cercanías y mercancías: un cierre en la alta velocidad afecta a más trenes de los que la simulación enumera. Los trenes de Ouigo no paran entre Madrid y Córdoba, de modo que su paso por cada tramo es siempre estimado.
- El fichero de Ouigo vale hasta el 12 de diciembre de 2026: para un día posterior, la simulación solo cuenta los trenes de Renfe.
- El cierre se supone de todas las vías del tramo, sin desvíos ni reordenación; las alternativas solo se señalan.
- La estimación proporcional ignora paradas técnicas y limitaciones temporales de velocidad.
