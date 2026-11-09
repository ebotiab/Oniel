# Simulación de cierre de un tramo

La simulación responde a una pregunta sencilla: **si este tramo se cerrase tal día entre tal hora y tal otra, ¿qué trenes se verían afectados?** Es una herramienta secundaria del visor; el objetivo principal de Oniel es entender cómo está conectada la red.

## Qué datos usa

- La red cargada: nodos (estaciones, PAET, PB, bifurcaciones, cambiadores) con su kilómetro en cada línea y tramos entre nodos consecutivos.
- Los horarios publicados por Renfe en su GTFS (`backend/data/raw/renfe/`): para cada tren, sus paradas con hora de llegada y salida.
- Una asignación curada de cada parada GTFS a la red, por línea (`stop_mappings` en `backend/data/curated/<línea>.json`): o la parada es un nodo de la línea, o está fuera y el tren entra o sale de la línea por un nodo concreto (por ejemplo, Málaga sale de la LAV por la bifurcación de Málaga; Jaén sale de la línea convencional por Espelúy).
- Las reglas de recorrido (`route_overrides`) para los trenes que cambian de línea a mitad de camino: dicen entre qué paradas el viaje va por cada línea y por qué nodo sale hacia la otra.

## Cómo se calcula el paso de un tren por un tramo

Está implementado en `backend/src/oniel/sim/passes.py` y se precalcula en la importación, línea a línea.

1. **Publicado.** Si el tren para en las dos estaciones que delimitan el tramo, entra a la hora de salida de la primera y sale a la hora de llegada de la segunda. Sin margen.
2. **Estimado.** Si no para en uno de los extremos, repartimos el tiempo entre sus dos paradas publicadas en proporción a la distancia recorrida por la línea. Margen de incertidumbre: 15 % del tiempo entre esas paradas, con un mínimo de 3 minutos. El extremo que sí coincide con una parada mantiene su hora publicada sin margen.
3. **Estimado con una parada fuera de la red.** Si una de las paradas está fuera de la línea cargada, el reparto usa la distancia por la línea hasta el nodo de salida más la distancia en línea recta desde ese nodo hasta la parada exterior. Margen: 30 %, mínimo 5 minutos.
4. **Estimado con una parada en otra línea cargada.** Un tren que cambia de línea se resuelve en cada una solo entre las paradas que le corresponden, según su regla de recorrido. En la línea que deja, la primera parada de la otra línea es una salida; si la asignación dice por qué nodo enlaza con la otra línea (`via`), la distancia desde la salida hasta esa parada se mide en línea recta hasta el nodo de enlace y por la otra línea desde ahí, en vez de toda en línea recta. Margen: 30 %, mínimo 5 minutos, y la explicación del paso dice en qué línea está la parada y por dónde sale o entra el tren.
5. **Indeterminado.** Si el horario incluye una parada que no sabemos situar, o las dos paradas de un trayecto están fuera de la red, no podemos fijar el recorrido: el paso queda indeterminado.

## Cómo se decide si un tren está afectado

Está en `backend/src/oniel/sim/closure.py`. Para cada tren que recorre el tramo el día elegido (y los del día anterior que terminan después de medianoche) comparamos la ventana con su intervalo de paso:

- Si ni siquiera con los márgenes se tocan → **no afectado**.
- Si se solapan aun descontando los márgenes → **afectado** (publicado o estimado, según el origen del dato).
- Si solo se tocan dentro del margen de incertidumbre, o el paso era indeterminado → **indeterminado**.

Las ventanas que terminan antes de empezar (23:00 a 01:00) se interpretan como que acaban al día siguiente.

## Recorrido alternativo

Desde que Oniel carga dos líneas que comparten Madrid-Puerta de Atocha y Córdoba, el resultado de un cierre dice también si **existe otro recorrido cargado** que salve el tramo. El cálculo está en `network_repo.fetch_alternatives`: se buscan, en la línea del tramo cerrado, los nodos que también pertenecen a otra línea y quedan uno antes y otro después del tramo; si una misma línea tiene uno a cada lado, se toma el par más cercano al tramo y se informa de la longitud por cada línea, de las estaciones principales intermedias y de los kilómetros de vía única del recorrido alternativo.

Ejemplos:

- Cierre de Villanueva de Córdoba – Adamuz (LAV): alternativa por la línea convencional entre Madrid-Puerta de Atocha y Córdoba, 440,7 km por Aranjuez, Alcázar de San Juan, Manzanares, Valdepeñas, Santa Cruz de Mudela, Vilches, Linares-Baeza y Andújar frente a 343,6 km por la alta velocidad, con 194 km de vía única.
- Cierre de Venta de Cárdenas – Vilches (convencional, Despeñaperros): alternativa por la LAV entre los mismos dos nodos, 343,6 km frente a 440,7 km.
- Cierre de Bifurcación Málaga – Majarabique (LAV): sin alternativa cargada, porque al sur de Córdoba Oniel solo tiene una línea.

Lo que **no** hace la simulación, y haría falta para un desvío real:

1. Decidir qué trenes afectados podrían tomar la alternativa. Depende del material (un AVE de ancho estándar no puede circular por la red convencional de ancho ibérico; un Alvia o un Intercity de ancho variable sí, cambiando de ancho en un cambiador que hoy no está modelado como requisito) y de si el tren tiene paradas intermedias que la alternativa no sirve.
2. Estimar el nuevo horario: tiempo de recorrido por la otra línea a sus velocidades (`segments.typical_speed_kmh` ya está disponible) y huecos en la ocupación de la vía única, donde los cruces limitan cuántos trenes caben por hora en cada sentido.
3. Deducir por sí sola el recorrido de un tren que cambia de línea: hoy hay que declararlo en una regla de recorrido de cada especificación, como se hizo con los Intercity y Alvia Madrid-Atocha Cercanías–Andalucía (véase `docs/datos.md`).
4. Tener en cuenta la situación real de la infraestructura: el corte por obras al sur de Venta de Cárdenas hasta otoño de 2027 significa que, mientras dure, la alternativa por Despeñaperros no está disponible aunque la geometría exista.

## Trenes que recorren las dos líneas

Los horarios de Renfe del 8 al 15 de noviembre de 2026 incluyen 24 Intercity y Alvia entre Madrid-Atocha Cercanías y Sevilla, Málaga, Ronda o Algeciras que tardan 2 h 50 entre Madrid y Ciudad Real y 1 h 15 entre Ciudad Real y Córdoba: el desvío por la red convencional que aparece en los horarios tras la interrupción de la alta velocidad en Urda. Cada línea los declara en `route_overrides`, y el resultado es el siguiente, tomando el Intercity 10270 (Madrid-Atocha Cercanías 6:00 → Ciudad Real 8:35/8:50 → Córdoba 9:45/9:50 → Sevilla 10:53) del viernes 13 de noviembre de 2026:

- En la línea convencional se resuelve entre Madrid y Ciudad Real, saliendo por Manzanares: 2 h 35 repartidas entre 196 km por la línea y 47 km en línea recta desde Manzanares hasta Ciudad Real. Pasos estimados en los once tramos Madrid–Manzanares (sale de Manzanares hacia las 8:05, margen de ±37 min) y ninguno más allá.
- En la LAV se resuelve desde Ciudad Real: paso publicado o estimado en Ciudad Real–Córdoba y Córdoba–Sevilla, y ninguno entre Madrid y Ciudad Real (ni en Urda–Ciudad Real).

Los 4 Alvia que no paran en Ciudad Real (Madrid–Córdoba en 3 h 45, el mismo tiempo que los anteriores) se tratan igual: en la convencional, Córdoba es para ellos una salida por Manzanares; en la LAV, Madrid-Atocha Cercanías es una entrada por Ciudad Real, y en ambos casos la distancia más allá de la salida se mide en línea recta hasta Ciudad Real o Manzanares y por la otra línea desde ahí. Las dos líneas reparten el mismo tiempo con la misma distancia total, así que la salida estimada de Manzanares (hacia las 7:46) precede a la entrada estimada en Ciudad Real (hacia las 8:11).

Está automatizado en `backend/tests/test_route_overrides.py`.

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
