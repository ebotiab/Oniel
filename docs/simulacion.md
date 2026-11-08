# Simulación de cierre de un tramo

La simulación responde a una pregunta sencilla: **si este tramo se cerrase tal día entre tal hora y tal otra, ¿qué trenes se verían afectados?** Es una herramienta secundaria del visor; el objetivo principal de Oniel es entender cómo está conectada la red.

## Qué datos usa

- La red cargada: nodos (estaciones, PAET, PB, bifurcaciones, cambiadores) con su kilómetro en la línea y tramos entre nodos consecutivos.
- Los horarios publicados por Renfe en su GTFS (`backend/data/raw/renfe/`): para cada tren, sus paradas con hora de llegada y salida.
- Una asignación curada de cada parada GTFS a la red (`stop_mappings` en `backend/data/curated/lav-madrid-sevilla.json`): o la parada es un nodo de la línea, o está fuera y el tren entra o sale de la línea por un nodo concreto (por ejemplo, Málaga sale por la bifurcación de Málaga; Huelva por el cambiador de Majarabique o por Santa Justa según pare o no en Sevilla).

## Cómo se calcula el paso de un tren por un tramo

Está implementado en `backend/src/oniel/sim/passes.py` y se precalcula en la importación.

1. **Publicado.** Si el tren para en las dos estaciones que delimitan el tramo, entra a la hora de salida de la primera y sale a la hora de llegada de la segunda. Sin margen.
2. **Estimado.** Si no para en uno de los extremos, repartimos el tiempo entre sus dos paradas publicadas en proporción a la distancia recorrida por la línea. Margen de incertidumbre: 15 % del tiempo entre esas paradas, con un mínimo de 3 minutos. El extremo que sí coincide con una parada mantiene su hora publicada sin margen.
3. **Estimado con una parada fuera de la red.** Si una de las paradas está fuera de la línea cargada, el reparto usa la distancia por la línea hasta el nodo de salida más la distancia en línea recta desde ese nodo hasta la parada exterior. Margen: 30 %, mínimo 5 minutos.
4. **Indeterminado.** Si el horario incluye una parada que no sabemos situar, o las dos paradas de un trayecto están fuera de la red, no podemos fijar el recorrido: el paso queda indeterminado.

## Cómo se decide si un tren está afectado

Está en `backend/src/oniel/sim/closure.py`. Para cada tren que recorre el tramo el día elegido (y los del día anterior que terminan después de medianoche) comparamos la ventana con su intervalo de paso:

- Si ni siquiera con los márgenes se tocan → **no afectado**.
- Si se solapan aun descontando los márgenes → **afectado** (publicado o estimado, según el origen del dato).
- Si solo se tocan dentro del margen de incertidumbre, o el paso era indeterminado → **indeterminado**.

Las ventanas que terminan antes de empezar (23:00 a 01:00) se interpretan como que acaban al día siguiente.

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
- `backend/tests/test_integration_db.py::test_closure_hand_case` (contra la base de datos y la API)
- `frontend/e2e/simulacion.spec.ts` (desde la interfaz)

Resultado completo de la API para ese caso (8 de noviembre de 2026): 96 trenes recorren el tramo ese día; 6 afectados con paso estimado, 5 indeterminados, 85 no afectados.

## Limitaciones conocidas

- Los horarios son los planificados por Renfe; no incluyen la interrupción vigente desde el 28 de octubre de 2026 ni otros cambios.
- Solo hay servicios de Renfe; faltan Iryo, Ouigo y mercancías.
- El cierre se supone de las dos vías, sin desvíos ni reordenación.
- La estimación proporcional ignora paradas técnicas y limitaciones temporales de velocidad.
