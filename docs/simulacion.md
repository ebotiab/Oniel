# Simulación de cierre de un tramo

La simulación responde a una pregunta sencilla: **si este tramo se cerrase tal día entre tal hora y tal otra, ¿qué trenes se verían afectados?** Es una herramienta secundaria del visor; el objetivo principal de Oniel es entender cómo está conectada la red.

## Qué datos usa

- La red cargada: nodos (estaciones, PAET, PB, bifurcaciones, cambiadores) con su kilómetro en cada línea y tramos entre nodos consecutivos.
- Los horarios publicados por Renfe en su GTFS (`backend/data/raw/renfe/`): para cada tren, sus paradas con hora de llegada y salida.
- Una asignación curada de cada parada GTFS a la red, por línea (`stop_mappings` en `backend/data/curated/<línea>.json`): o la parada es un nodo de la línea, o está fuera y el tren entra o sale de la línea por un nodo concreto (por ejemplo, Málaga sale de la LAV por la bifurcación de Málaga; Jaén sale de la línea convencional por Espelúy).
- Las reglas de recorrido (`route_overrides`) para los trenes que cambian de línea a mitad de camino: dicen entre qué paradas el viaje va por cada línea y por qué nodo sale hacia las otras.

## Cómo se calcula el paso de un tren por un tramo

Está implementado en `backend/src/oniel/sim/passes.py` y se precalcula en la importación, línea a línea.

1. **Publicado.** Si el tren para en las dos estaciones que delimitan el tramo, entra a la hora de salida de la primera y sale a la hora de llegada de la segunda. Sin margen.
2. **Estimado.** Si no para en uno de los extremos, repartimos el tiempo entre sus dos paradas publicadas en proporción a la distancia recorrida por la línea. Margen de incertidumbre: 15 % del tiempo entre esas paradas, con un mínimo de 3 minutos. El extremo que sí coincide con una parada mantiene su hora publicada sin margen.
3. **Estimado con una parada fuera de la red.** Si una de las paradas está fuera de la línea cargada, el reparto usa la distancia por la línea hasta el nodo de salida más la distancia en línea recta desde ese nodo hasta la parada exterior. Margen: 30 %, mínimo 5 minutos.
4. **Estimado con una parada en otra línea cargada.** Un tren que cambia de línea se resuelve en cada una solo entre las paradas que le corresponden, según su regla de recorrido. En la línea que deja, la primera parada de la otra línea es una salida, y su asignación dice por dónde se llega a ella (`via`): la línea y el nodo por el que el tren entra. La distancia desde la salida hasta esa parada se mide entonces por esa línea, no en línea recta; solo si la salida y el nodo de enlace son puntos distintos se añade la línea recta entre los dos. Margen: 30 %, mínimo 5 minutos, y la explicación del paso dice en qué línea está la parada y por dónde sale o entra el tren.
5. **Estimado a través de varias líneas.** Un viaje puede recorrer tres líneas o más. El modelo sigue resolviéndolo línea a línea; lo que cambia es que el camino hasta una parada puede cruzar más de una línea, y entonces `via` es una lista de trechos: cada uno entra en su línea por un nodo y la deja en el nodo del trecho siguiente, que tiene que ser común a las dos, y el último llega a la parada. La distancia es la suma de los kilómetros de cada trecho por su línea. Si el tren cruza una línea entera sin parar en ella, sus dos paradas quedan fuera, una a cada lado; cuando a las dos se llega por líneas cargadas, el recorrido está fijado (entra por un nodo y sale por otro) y el paso es estimado. Margen: 30 % del mayor de los dos tiempos que el tren pasa fuera de la línea (de la parada anterior a la entrada, o de la salida a la parada siguiente), mínimo 5 minutos; es el margen que las líneas vecinas dan a esos mismos puntos de enlace.
6. **Indeterminado.** Si el horario incluye una parada que no sabemos situar, o las dos paradas de un trayecto están fuera de la línea y no se llega a ambas por líneas cargadas, no podemos fijar el recorrido: el paso queda indeterminado.

## Cómo se decide si un tren está afectado

Está en `backend/src/oniel/sim/closure.py`. Para cada tren que recorre el tramo el día elegido (y los del día anterior que terminan después de medianoche) comparamos la ventana con su intervalo de paso:

- Si ni siquiera con los márgenes se tocan → **no afectado**.
- Si se solapan aun descontando los márgenes → **afectado** (publicado o estimado, según el origen del dato).
- Si solo se tocan dentro del margen de incertidumbre, o el paso era indeterminado → **indeterminado**.

Las ventanas que terminan antes de empezar (23:00 a 01:00) se interpretan como que acaban al día siguiente.

## Recorrido alternativo

Desde que Oniel carga líneas que comparten nodos (Madrid-Puerta de Atocha y Córdoba, la alta velocidad y la convencional; Manzanares y Ciudad Real, la tercera con cada una de las otras), el resultado de un cierre dice también si **existe otro recorrido cargado** que salve el tramo. El cálculo está en `network_repo.fetch_alternatives`: se buscan, en la línea del tramo cerrado, los nodos que también pertenecen a otra línea y quedan uno antes y otro después del tramo; si una misma línea tiene uno a cada lado, se toma el par más cercano al tramo y se informa de la longitud por cada línea, de las estaciones principales intermedias y de los kilómetros de vía única del recorrido alternativo.

Ejemplos:

- Cierre de Villanueva de Córdoba – Adamuz (LAV): alternativa por la línea convencional entre Madrid-Puerta de Atocha y Córdoba, 440,7 km por Aranjuez, Alcázar de San Juan, Manzanares, Valdepeñas, Santa Cruz de Mudela, Vilches, Linares-Baeza y Andújar frente a 343,6 km por la alta velocidad, con 194 km de vía única.
- Cierre de Venta de Cárdenas – Vilches (convencional, Despeñaperros): alternativa por la LAV entre los mismos dos nodos, 343,6 km frente a 440,7 km.
- Cierre de Bifurcación Málaga – Majarabique (LAV): sin alternativa cargada, porque al sur de Córdoba Oniel solo tiene una línea.
- Cierre de Urda – Ciudad Real (LAV): la alternativa señalada es la convencional entera entre Madrid-Puerta de Atocha y Córdoba. El recorrido más corto, por la convencional hasta Manzanares y por la línea de Manzanares a Ciudad Real (260,5 km frente a 170,8 km), no aparece: usa dos líneas, y la búsqueda solo considera una.
- Cierre de Almagro – Ciudad Real (línea de Manzanares a Ciudad Real): sin alternativa, porque ninguna otra línea tiene un nodo a cada lado del tramo. El rodeo existe (por la convencional hasta Madrid y por la alta velocidad hasta Ciudad Real), pero también necesita dos líneas.

Lo que **no** hace la simulación, y haría falta para un desvío real:

1. Decidir qué trenes afectados podrían tomar la alternativa. Depende del material (un AVE de ancho estándar no puede circular por la red convencional de ancho ibérico; un Alvia o un Intercity de ancho variable sí, cambiando de ancho en un cambiador que hoy no está modelado como requisito) y de si el tren tiene paradas intermedias que la alternativa no sirve.
2. Estimar el nuevo horario: tiempo de recorrido por la otra línea a sus velocidades (`segments.typical_speed_kmh` ya está disponible) y huecos en la ocupación de la vía única, donde los cruces limitan cuántos trenes caben por hora en cada sentido.
3. Deducir por sí sola el recorrido de un tren que cambia de línea: hoy hay que declararlo en una regla de recorrido de cada especificación, como se hizo con los Intercity y Alvia Madrid-Atocha Cercanías–Andalucía (véase `docs/datos.md`).
4. Encontrar alternativas que encadenen varias líneas, como la de Madrid a Ciudad Real por Manzanares. Es lo que pide el comparador de recorridos de la hoja de ruta.
5. Tener en cuenta la situación real de la infraestructura: el corte por obras al sur de Venta de Cárdenas hasta otoño de 2027 significa que, mientras dure, la alternativa por Despeñaperros no está disponible aunque la geometría exista.

## Trenes que recorren varias líneas

Los horarios de Renfe del 8 al 15 de noviembre de 2026 incluyen 24 Intercity y Alvia entre Madrid-Atocha Cercanías y Sevilla, Málaga, Ronda o Algeciras que tardan 2 h 50 entre Madrid y Ciudad Real y 1 h 15 entre Ciudad Real y Córdoba: el desvío por la red convencional que aparece en los horarios tras la interrupción de la alta velocidad en Urda. Van por la convencional hasta Manzanares, por la línea de Manzanares a Ciudad Real y, desde Ciudad Real, por la alta velocidad. Cada una de las tres líneas los declara en `route_overrides`, y el resultado es el siguiente, tomando el Intercity 10270 (Madrid-Atocha Cercanías 6:00 → Ciudad Real 8:35/8:50 → Córdoba 9:45/9:50 → Sevilla 10:53) del viernes 13 de noviembre de 2026:

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
- `backend/tests/test_integration_db.py::test_closure_hand_case` (contra la base de datos y la API, incluida la alternativa por Alcázar)
- `frontend/e2e/simulacion.spec.ts` (desde la interfaz)

Resultado completo de la API para ese caso (8 de noviembre de 2026): 96 trenes recorren el tramo ese día; 6 afectados con paso estimado, 5 indeterminados, 85 no afectados.

## Limitaciones conocidas

- Los horarios son los planificados por Renfe; no incluyen la interrupción de la alta velocidad vigente desde el 28 de octubre de 2026, el corte de la línea convencional al sur de Venta de Cárdenas ni otros cambios.
- Solo hay servicios de Renfe; faltan Iryo, Ouigo, Cercanías y mercancías.
- El cierre se supone de todas las vías del tramo, sin desvíos ni reordenación; la alternativa solo se señala.
- La estimación proporcional ignora paradas técnicas y limitaciones temporales de velocidad.
