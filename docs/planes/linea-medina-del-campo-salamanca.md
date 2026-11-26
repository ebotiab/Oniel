# Línea convencional Medina del Campo – Salamanca y acceso desde Medina AV

**[Incidencia de implementación #320][tarea] · Estudio del 26 de noviembre de 2026.** El tren de Palencia a Salamanca-La Alamedilla y el de Madrid-Chamartín a Salamanca entran por estaciones distintas de Medina del Campo. Empiezan a compartir la línea 120 en la **bifurcación Arroyo de la Golosa**, antes de Campillo. En el extremo salmantino, los trenes de Ávila se incorporan por otro acceso. Para seguir cualquiera de estos viajes basta un eje por tramo, una ficha por estación y el viaje que Renfe ya publica.

Se revisaron el [`main` 9d3679b][base], los planes y las incidencias y PR abiertas y cerradas sobre Salamanca. [#317][pr-avila] preparó Ávila–Salamanca y dejó los dos accesos de Medina a trazos. [#315][pio] ya incorporó Príncipe Pío–Pinar. **La carga de Medina espera a que [#316][avila] esté entregada en `main`**. Los nombres del [plan de Ávila][plan-avila] son propuestas. Al recoger el turno, localizar en la red resultante las fichas, las agujas y el propietario de cada tramo, y usar los IDs que se hayan publicado. La investigación documental es independiente de [Grisén, #310][grisen]. La futura importación necesita un turno de datos exclusivo, también respecto a los refrescos GTFS. Cercanías y la prolongación desde La Alamedilla hacia Portugal quedan fuera.

## Qué conectar en Medina

| Entrada del tren | Camino hasta Arroyo de la Golosa | Cambio en el atlas |
|---|---|---|
| Valladolid → **Medina del Campo**, `10500`, nodo existente `medina-del-campo` de la 100 | Desde las vías de la estación convencional sale hacia el suroeste la 120 de ancho ibérico. En la relación OSM 6016262 se puede seguir la vía 7 hacia Salamanca. En la cabecera norte la misma relación llega a la aguja 12 (`3886457822`) hacia Valladolid. Adif anuncia también servicios por otras vías de la estación. | Conservar la ficha, el acceso desde Pozaldez y la posición de la 100. Iniciar ahí la línea principal `medina-del-campo-salamanca` en Castilla y León. Anclar su geometría a la estación existente. Sustituir `conv-medina-salamanca` cuando esté cargado el camino hasta el acceso salmantino. |
| Chamartín → Segovia-Guiomar → **Medina del Campo AV**, `08240`, nodo existente `medina-del-campo-av` de la LAV de Olmedo a Ourense | Desde la 982 se entra en la 190, de ancho estándar. En el cambiador de **Medina AV** los trenes pasan al ancho ibérico de la 188, que desemboca en la 120 en Golosa. Adif sitúa allí el PK 0,000 de la 188 y el 6,846 de la 120. El cambiador está en el PK 3,000 de la 188. | Representar el ramal como enlace de la LAV (`link_of`), con el cambiador como nodo técnico y final en Golosa. Reutilizar el eje AV desde la estación hasta la salida elegida. Sustituir `enlace-medina-salamanca` al acreditar la continuidad completa del enlace. |

Los dos croquis tienen hoy `status: no_cargada`, un solo `node_id` y la misma punta en Salamanca, `[-5.64899, 40.972235]`. Uno parte de `[-4.909678, 41.31726]`, el otro de `[-4.9229851, 41.2913315]`. Son rectas orientativas. El GTFS del 17 sitúa incluso las coordenadas de `08240` cerca de la estación convencional. Conservar ambos códigos y sus posiciones verificadas en Oniel. Si falta un empalme acreditado al cargar, mantener el croquis correspondiente como pendiente, fuera de rutas y cierres. Conservar la conexión por Toro de la convencional de Zamora, la salida AV hacia Zamora y las conexiones de Ávila que haya resuelto #316. [Especificación de la 100][conv] · [especificación de la LAV][lav] · [costuras del modelo][costuras].

**Corte del enlace AV.** En el sentido Madrid–Salamanca la relación OSM pasa por `4934361912` después de la estación. Su proyección sobre el tramo exportado Medina AV–Toro dista unos 5 m del eje, a 0,664 km de su principio. Se propone partir ese tramo a dicha altura, asignar estación–salida una sola vez a la LAV y empezar en la salida las aristas del enlace. En sentido Madrid hay una vía de andén distinta que se une al mismo ramal en `4934361913`. La tabla de geometría permite comprobar los dos caminos. La proyección enlaza los ejes del atlas, sin identificar físicamente dos agujas paralelas. Comprobar los giros desde/hacia Olmedo y Salamanca y el paso recto hacia Toro. Excluir los atajos que exigirían invertir la marcha en la aguja AV o en Golosa. `bif-medina` está junto a Olmedo, donde se separan las LAV de Valladolid y Galicia. [Adif, 190][dr-av] · [Adif, 188 y 120][esquema] · [OSM hacia Salamanca][ida] · [OSM hacia Madrid][vuelta].

## Estaciones y límites de la línea propia

La tabla sigue la 120 en el sentido de Medina a Salamanca. La columna de PK procede de la lámina «Salamanca» de Adif. La última columna mide sobre el eje OSM elegido desde la parada convencional. Para las ocho paradas intermedias se proyectaron los puntos de `stops.txt` del 17/11 sobre ese eje. El mayor desplazamiento lateral es de unos 89 m, en Cantalapiedra. Contrastar allí la posición con el andén antes de fijar la ficha. [Esquema de Adif, p. 52 del PDF][esquema] · [horario registrado][fuentes].

| Lugar | Código de parada | PK de referencia | Km medidos aprox. | Función |
|---|---|---:|---:|---|
| Medina del Campo | 10500 | Origen de la 120 | 0,0 | Estación compartida con la 100 |
| Arroyo de la Golosa | — | 6,846 | 6,8 | Unión de la 188 y la 120, sin parada |
| Campillo | 32001 | 11,829 | 11,8 | Parada comercial |
| El Carpio | 32002 | 21,310 | 21,3 | Parada comercial |
| Fresno el Viejo | 32003 | 24,725 | 24,7 | Parada comercial |
| Cantalapiedra | 32004 | 32,230 | 32,2 | Parada comercial |
| Cantalpino | — | 42,600 | — | Instalación del esquema, sin parada en las tres ediciones. Verificar su función actual antes de crear ficha |
| El Pedroso de la Armuña | 32006 | 52,574 | 52,3 | Parada comercial |
| Pitiegua | 32007 | 58,574 | 58,4 | Parada comercial |
| Gomecello | 32008 | 64,852 | 64,6 | Parada comercial |
| Moriscos | 32009 | 69,724 | 69,5 | Parada comercial |
| Unión con el acceso de Ávila | — | Pendiente | 76,0 | Final del tramo propio, `bif-acceso-salamanca` en la propuesta #316 |
| Salamanca | 30100 | 76,825 | 76,5 | Estación principal de #316 |
| Salamanca-La Alamedilla | 30110 | 0,900 desde Salamanca | 77,3 | Apeadero de #316. Solo llegan los viajes que lo publican |

### Geometría reproducible y comprobación de la cabecera salmantina

Cada fila recorta **vías por dos nodos OSM**, en orden. El itinerario base del atlas aprovecha la vía general de Campillo, miembro de la relación hacia Salamanca. La 6016262 elige allí el apartado `742586819` entre las mismas agujas que la general `293322141`. Una parada en Campillo por sí sola no determina por cuál pasó el tren. Las relaciones son de servicio y su nombre «Alvia» tampoco determina el producto del GTFS. [120 desde Medina][r120] · [Madrid–Salamanca][ida] · [Salamanca–Madrid][vuelta].

| Recorte | Relación y versión | Desde → hasta | Control de vía | Km |
|---|---|---|---|---:|
| Medina convencional → Golosa | 6016262 v49 | `14361619895 → 2232327713` | `228411273`, `666625431`, `1513727189` | 6,777 |
| Andén AV → salida de la 982 hacia Salamanca | 20685324 v4 | `6329564866 → 4934361912` | `387370782`, diagonal `972351058`, `1513727186` | 0,670 |
| Salida 982 → cambiador | 20685324 v4 | `4934361912 → 4934361918` | 190 por `1513727187`, `503093156`, `1442229459` | 0,460 |
| Comprobación del otro andén AV → cambiador, medida en orden inverso al servicio de vuelta | 20685325 v3 | `6340046033 → 4934361918` | `503093162`, `972360595` hasta `4934361913`, luego 190 | 1,115 |
| Cambiador → Golosa | 20685324 v4 y 20685325 v3 | `4934361918 → 2232327713` | 188 por `1442229460`, `386743040`, `1442229462` | 2,948 |
| Golosa → unión propuesta con Ávila | 20685324 v4 y 20685325 v3 | `2232327713 → 33246283` | `742586820`, general de Campillo `293322141`, `742207571` en Gomecello, `42998322` en la entrada | 69,207 |
| Unión → principal → La Alamedilla, eje de #316 | 6016262 v49 | `33246283 → 33246281 → 495082202` | `1513727190` en la unión, vía 2 en la principal. Cadena completa en el [plan de Ávila][plan-avila] | 0,481 + 0,833 |

**Una salvedad en Salamanca.** Las dos relaciones AV pasan por `33246283` y comparten los primeros 80 m de la propuesta de #316 hasta `592687639`. Allí se desvían por `400830381` y `400830382` hasta `13829159897`, vía 1 (0,484 km desde la unión). El panel de Salamanca del 26/11 anuncia el 04899 por vía 1, el 18901 de Ávila por vía 5 y el 18308 por vía 1. Esto respalda conservar la unión y la ficha única de la estación. La arista unión–principal representa el acceso a la estación en conjunto. Un paso por esa arista o su cierre en el simulador se refiere al conjunto representado. Para atribuir un cierre a una vía de andén individual haría falta el itinerario de ese servicio y día. La prolongación desde la principal se apoya en los horarios y en el eje ya estudiado en #316. [Panel de Salamanca][sal] · [OSM de llegada][ida] · [propuesta del acceso común][plan-avila].

Para repetir las medidas desde `backend/`, con el entorno de Oniel, ejecutar este bloque con `uv run python`. Lee los originales de la API 0.6 en memoria. El trazador del repositorio usa las vías miembro con `railway=rail`, conecta por ID y pondera cada par consecutivo por distancia de Haversine. La igualdad de extremos evita aceptar una vía próxima por error. Si ha cambiado la versión, recuperar el estado del **26/11/2026** en el historial de OSM (incluidas las versiones de vías y nodos) o documentar el cambio y medir de nuevo.

```python
import json
from urllib.request import urlopen

from oniel.network.build import trace_osm_relation

cortes = {
    (6016262, 49): [(14361619895, 2232327713), (33246283, 33246281),
                    (33246281, 495082202)],
    (20685324, 4): [(6329564866, 4934361912), (4934361912, 4934361918),
                    (4934361918, 2232327713), (2232327713, 33246283),
                    (33246283, 13829159897)],
    (20685325, 3): [(6340046033, 4934361918), (4934361918, 2232327713),
                    (2232327713, 33246283), (33246283, 13829159897)],
}
for (rel, version), pares in cortes.items():
    with urlopen(f"https://api.openstreetmap.org/api/0.6/relation/{rel}/full.json") as fh:
        original = json.load(fh)
    elementos = original["elements"]
    assert any(e["type"] == "relation" and e["id"] == rel and e["version"] == version
               for e in elementos)
    xy = {e["id"]: (e["lon"], e["lat"]) for e in elementos if e["type"] == "node"}
    for a, b in pares:
        eje = trace_osm_relation(original, rel, xy[a], xy[b]).polyline
        assert (eje.coords[0], eje.coords[-1]) == (xy[a], xy[b])
        print(rel, a, b, round(eje.length_km, 3))
```

### Atributos por sección

| Sección | Ancho, vías y energía | Velocidad, protección, bloqueo y mando |
|---|---|---|
| 10500 → PK 4,5 de la 120 | 1.668 mm, 3 kV CC. Adif clasifica la 120 como vía única. OSM señala dos vías de viajeros en la salida paralela al corredor de Zamora. Contar solo las generales de la 120 y documentar el límite de la playa de Medina | OSM indica 50 km/h hasta `2359248743` y después 155. En la 120 rigen ASFA convencional, BLAU y CTC, con la excepción indicada abajo. Revisar los límites interiores de estación |
| PK 4,5 → Golosa → Campillo | Vía única de 1.668 mm con 25 kV 50 Hz. El cambio de tensión que sitúa Adif en el PK 4,5 coincide con el cambio de etiqueta en `6242295526` | 155 en la general. Hasta Golosa, BLAU con CTC. **Golosa–Campillo tiene BAU con CTC** según la tabla de capacidad de Adif |
| Campillo → Moriscos → unión en Salamanca | General única de 1.668 mm con 25 kV 50 Hz. Apartaderos de cruce en estaciones | ASFA, BLAU y CTC. OSM marca 155 salvo, en este recorte, 135 en `742207571`, entre `255330289` y `255330284` en Gomecello. Calcular máxima y predominante por longitud de cada tramo |
| Estación AV → salida → cambiador | Conservar la sección de la 982 que se aproveche. La 190 es de 1.435 mm y 25 kV. Una vía en la rama elegida después de la salida | OSM marca 30 y 20 km/h en la 190 y ETCS nivel 2. Confirmar protección efectiva, bloqueo, mando y velocidades de agujas en la cabecera. Al partir Medina AV–Toro, revisar el límite de doble a única ya documentado en la LAV |
| Cambiador → Golosa (188) | General única, 1.668 mm y 25 kV 50 Hz. El cambio de ancho se identifica en `4934361918` | En OSM, sucesivamente 20, 30, 70 y 100 km/h. En su puesta en servicio se documentaron ASFA, BAU y CTC. Verificar vigencia y límites del cambiador |
| Unión en Salamanca → principal → apeadero | Conservar los atributos de los tramos que entregue #316 | Siguen pendientes las velocidades locales y el límite operativo de la catenaria por vía en la playa. No extender la velocidad del tronco a la principal ni al apeadero |

El mapa 3 de la DR y la tabla de capacidad dan **155 km/h entre Medina y Salamanca**. Los 200 km/h de la nota de energía de Adif se refieren al ámbito de 202 km hasta Fuentes de Oñoro. Para el corredor estudiado prevalecen las fuentes que lo delimitan. BAU y BLAU son dos sistemas de bloqueo en vía única. CTC es control de tráfico centralizado. Registrar por sección `tracks`, ancho, tensión y señalización, con fuente y fecha. Dejar sin valor la velocidad local desconocida y usar `sin_dato_publicado` donde el modelo lo admita para señalización. Si falta una sección obligatoria de vías con respaldo, resolverla antes de importar. [Adif, estrategia de capacidad, tabla de la L120][cap] · [mapas 3 y 4, pp. 7–8][mapas] · [Adif, energía][energia] · [Ministerio, puesta en servicio de la 188, pp. 66–67][informe] · [atributos de Oniel][atributos].

## Servicios que debe conservar la carga

Se leyeron los ZIP del [registro de Oniel][fuentes] con el lector del proyecto, que aplica el calendario y las excepciones y resuelve las variantes coincidentes de un número en un día. Las tres ediciones Renfe se solapan. Cada columna histórica cuenta viajes normalizados de **una edición completa**. El control diario usa la del 17/11. Los otros tres operadores registrados dan cero coincidencias. [Renfe, GTFS AV/LD/MD][gtfs] · [regla de variantes][variantes] · [selección de conjunto por fecha][conjuntos].

| Entrada | 08/11 | 12/11 | 17/11 | Hacia Salamanca el jueves 26/11 | Desde Salamanca ese día |
|---|---:|---:|---:|---|---|
| Medina convencional, 10500 | 44 | 41 | 41 | 7. Cinco llegan a La Alamedilla y dos a la principal | 7, todos desde la principal |
| Medina AV, 08240 | 50 | 50 | 50 | 4 a la principal | 4 desde la principal |
| Ávila por Peñaranda, control de #316 | 73 | 71 | 71 | 7 a La Alamedilla | 7 desde la principal |

Se reproduce el censo de #316. Los tres viajes de diferencia entre 44 y 41 corresponden a una variante menos de cada uno de los números 00631, 00632 y 18324 en los dos ZIP posteriores. Las ediciones del 8 y 12 rotulan los de Medina AV como Alvia y los convencionales como Media Distancia, Regional Exprés o Intercity. En la del 17 figuran Intercity por Medina AV, y Regional o Intercity por la convencional. Conservar los rótulos de cada edición. Un panel de estación puede usar otro nombre comercial.

**Patrones de la edición del 17.** En la columna de paradas intermedias se abrevian los códigos `320xx` por sus dos últimas cifras. El orden es el de marcha. «Directo» significa que entre esa Medina y Salamanca principal el horario carece de parada comercial. El tren sigue recorriendo los tramos intermedios. Salvo los números entre paréntesis, todos figuran el jueves 26/11.

| Origen → terminal | Número | Paradas entre Medina y Salamanca principal |
|---|---|---|
| Valladolid-Campo Grande → La Alamedilla | 18300 | 02, 03, 04, 06, 07, 08, 09 |
| Valladolid-Campo Grande → La Alamedilla | 18304, 18316 | Directo |
| Valladolid-Campo Grande → La Alamedilla | 18318 | 02, 03, 04, 08 |
| Palencia → La Alamedilla | 18308 | 01, 02, 03, 04, 06, 08 |
| Valladolid-Campo Grande / Zaragoza-Delicias → Salamanca principal | 37432 / 00632 | Directo |
| Salamanca principal → Valladolid-Campo Grande | 18302, 18310, 18314, (18324) | Directo |
| Salamanca principal → Valladolid-Campo Grande | 18312 | 08, 07, 06, 04, 03, 02, 01 |
| Salamanca principal → Valladolid-Campo Grande / Zaragoza-Delicias | 37431 / 00631 | 04, 03, 02 |
| Salamanca principal → Palencia | 18306 | 09, 08, 07, 06, 04, 03, 02 |
| Chamartín → Segovia-Guiomar → Medina AV → Salamanca principal | 04899, 04929, 04969, 04909, (04809) | Directo |
| Salamanca principal → Medina AV → Segovia-Guiomar → Chamartín | 04868, 04918, 04958, 04988, (04898) | Directo |

Los paréntesis distinguen variantes de calendario. El sábado 28/11 sí figuran 18324, 04809 y 04898. En el acceso desde Valladolid hay trenes que paran en Viana, Valdestillas, Matapozuelos y Pozaldez y otros que van directos a Medina. Conservar las paradas exteriores tal como las da cada viaje. El 00631 sigue de Valladolid a Zaragoza por Burgos, Miranda, Vitoria, Pamplona y Tudela. Comparte horas hasta Valladolid con el 37431. El panel de Adif en Medina del 24/11 los identifica como servicio compartido. Conservar ambas ofertas y cabeceras en el censo por número de Oniel. Ese censo cuenta servicios publicados y no permite inferir el número de composiciones físicas. La programación del GTFS tampoco confirma por sí sola que el tren circulara en una fecha afectada por obras. [Panel de Medina convencional][adif-conv] · [horarios Renfe][gtfs].

Para reproducir el censo y ver la secuencia completa de cada servicio del jueves, ejecutar desde la raíz con `PYTHONPATH=backend/src python -`. Solo lee los tres ZIP.

```python
from collections import Counter
from datetime import date
from pathlib import Path

from oniel.gtfs.reader import read_feed

dia = date(2026, 11, 26)
for zip_renfe in sorted(Path("backend/data/raw/renfe").glob("*.zip")):
    horario = read_feed(zip_renfe)
    edicion, diarios = Counter(), Counter()
    for tren in horario.trips.values():
        paradas = [p.stop_id for p in tren.stop_times]
        if "30100" not in paradas:
            continue
        acceso, = (p for p in ("10500", "08240", "34010") if p in paradas)
        edicion[acceso] += 1
        if dia in horario.service_dates[tren.service_id]:
            diarios[acceso, paradas.index(acceso) < paradas.index("30100"), paradas[-1]] += 1
            if "11-17" in zip_renfe.name:
                print(tren.train_number, tren.product, *paradas)
    print(zip_renfe.name, edicion, diarios)
```

**Asignación en el importador.** Reutilizar el viaje normalizado y su calendario en todas las líneas que recorra. Una estación es un nodo compartido. Un tramo físico tiene un propietario y un solo ID. El filtro y las reglas de recorrido de la línea propietaria deben producir el paso por ese tramo. En las vecinas, las asignaciones de salida y `via` permiten calcular la distancia al continuar el viaje. El identificador de servicio del paso se conserva al cruzar los límites. Comparar antes y después el conjunto de viajes únicos por edición y las parejas de servicio y tramo por fecha. Los 22 servicios de Medina del jueves ya se reconocen en la 100 o en la LAV.

- En la 100 conservar las excepciones bidireccionales `salamanca-por-medina-30100/32002/32001`, que detectan la pareja consecutiva de `10500` con Salamanca, El Carpio o Campillo. Completar las salidas por Medina con la distancia de la 120 y los `via` hasta el acceso de #316. Preservar los recorridos sin parada intermedia y la salida hacia Peñaranda por Ávila que entregue #316.
- En la 982, los trenes con el par `08240 ↔ 30100` salen por el enlace hacia Golosa. Mantener su recorrido anterior por Olmedo y Segovia. En el nuevo enlace, exigir ese par en estos horarios. En la 120 distinguir los viajes con `10500` y `30100` de los que llegan por el cambiador con `08240` y `30100`. Estos últimos solo ganan pasos desde Golosa hacia Salamanca. Probar los dos sentidos. No exigir una de las ocho paradas interiores, porque se perderían los directos.
- En el acceso salmantino, iniciar o terminar el recorrido en la unión que entregue #316. Respetar `30100`, `30110`, sus horas y permisos. Pasar por una aguja genera un paso estimado, sin hora comercial ni llamada de viajeros. Mantener la selección por Peñaranda de los regionales de la 122. Evitar que un tren por Medina recorra la 122 o que un tren por Ávila recorra la 120 al este de su unión. [Reglas actuales de la 100][conv] · [reglas de la LAV][lav] · [casos de Ávila][plan-avila].

## Aceptación de la futura PR de datos

Usar los días de servicio indicados y el GTFS del 17/11 como referencia reproducible. Si entra una edición nueva, conservar este control histórico y explicar cualquier cambio en la edición aplicable. Los tiempos de la tabla son comerciales. El comparador de infraestructura calcula aparte el tiempo sin paradas.

1. **Acceso convencional, ambos sentidos.** El 26/11, seguir el 18308 desde Palencia (13:25), por Valladolid, Medina convencional (14:36–14:37), Golosa, Campillo (14:46), Salamanca principal (15:42–15:44, solo bajada) y La Alamedilla (15:46). Cerrar Campillo–El Carpio de 14:46 a 14:58 y localizar un único paso afectado del 18308. En la vuelta, el 18312 sale de la principal a las 20:45 y alcanza Medina convencional a las 21:44. Ninguno pasa por el cambiador ni por Peñaranda.
2. **Acceso AV, ambos sentidos.** El 04899 sale de Chamartín a las 08:50, para en Segovia-Guiomar y en Medina AV (09:45–09:47), cambia de ancho, se incorpora en Golosa y termina en la principal a las 10:31. El 04868 recorre el camino inverso desde Salamanca a las 06:25, pasa por Medina AV a las 07:06–07:08 y llega a Chamartín a las 08:05. Un único viaje extremo a extremo en las fichas. Cero pasos de estos números por 10500–Golosa, hacia Toro, por la 122 o por Salamanca–La Alamedilla.
3. **Control por Ávila y terminal urbana.** El 18901 de Príncipe Pío conserva Pinar, Ávila, Peñaranda y la principal (10:40–10:42) hasta La Alamedilla (10:45). El 18904 sale de la principal hacia Ávila. Cero pasos de ambos por Golosa. En 10500–Golosa se esperan 14 servicios y en el enlace del cambiador ocho. En Golosa–Campillo se esperan **22 servicios** ese jueves, 11 por sentido. En el eje agregado unión–principal deben seguir los mismos 36 del censo de #316 (14 de Ávila y 22 de Medina). En Salamanca–La Alamedilla se mantienen **12**, los siete de Ávila y los cinco de Medina (18300/04/08/16/18), sin añadirlos de nuevo a los que cargue #316. El cierre urbano de 15:44 a 15:47 alcanza al 18308 una sola vez. Comprobar permisos de subida/bajada tanto en destinos directos como en las fichas. [Aceptación complementaria de #316][plan-avila].
4. **Comparador en la API y en la instantánea.** En ambos sentidos probar `medina-del-campo ↔ salamanca`, `medina-del-campo-av ↔ salamanca`, ambos accesos hasta `salamanca-la-alamedilla` y `madrid-principe-pio ↔ salamanca` por Ávila. Identificar cada ruta por los nodos de paso aunque cambie su orden en la lista. Hasta la principal se esperan aproximadamente **76,5 km** desde la convencional, **73,8 km** desde AV y **231,4 km** desde Príncipe Pío por Ávila, sujetos al ajuste en las estaciones. Hasta el apeadero se suman unos **0,83 km**. Distinguir la existencia del recorrido en el grafo de la oferta directa del día. Comparar la respuesta de `GET /api/routes?from=…&to=…` con `findRoutes(buildGraph(…))` sobre `frontend/public/data/index.json`, con iguales escenario y límites. Exigir igualdad de `node_ids`, `segment_ids`, `line_ids`, kilómetros y `time_min` (incluida la ausencia de tiempo si falta velocidad). Repetir con cierre y en el visor estático. Para los servicios de la instantánea, usar su propia fecha y el mismo conjunto en API. La referencia de esta base es el 11/12, que también programa el 18308 y el 04899. [Pruebas de paridad][paridad] · [caso de integración de Príncipe Pío][e2e].
5. **Inventario, datos y entrega.** Verificar que solo haya un nodo para cada código de estación y una arista por trecho compartido, con geometría continua y giros practicables. Buscar ambas Medinas y ambas salmantinas en mapa, esquema y fichas. Las ocho paradas comerciales intermedias deben estar en orden. Revisar atributos y avisos de circulación para la fecha elegida. Resolver los límites locales pendientes o dejar constancia de la ausencia admitida antes de validar. [Procedimiento de carga][carga].

### Archivos y orden de integración

Primero cotejar la entrega de #316 en `main` y anotar el inventario de partida por conjunto y fecha. La carga añadiría las especificaciones de la 120 y del enlace AV en `backend/data/curated/`, tocaría `madrid-avila-valladolid.json`, `lav-olmedo-ourense.json` y los filtros o salidas del propietario del acceso de Salamanca. Revisar los `via` dependientes de la LAV. Registrar los originales nuevos con fecha en `backend/data/raw/` y su procedencia en `backend/data/curated/sources.json`. Dar de alta las especificaciones en `backend/src/oniel/settings.py` y en `SPECS` de `backend/tests/conftest.py`.

En el turno exclusivo, validar por especificación y la red entera con `uv run oniel-data validate`, importar una sola vez desde una base vacía de sesión con `uv run oniel-data import all` y cotejar `frontend/public/data/` (índice, líneas, nodos, tramos, histórico y alternativas). Ajustar pruebas de datos y recuentos afectados, `backend/tests/test_routing.py`, `frontend/e2e/fixtures/rutas-paridad.json` y casos focalizados de Playwright estáticos y `@api`. Actualizar el inventario en `AGENTS.md`, `docs/datos.md`, `docs/simulacion.md` y el seguimiento que corresponda al entregar. Documentar diferencias de pasos e identidades, pasar CI y verificar el commit importado en producción. [Añadir otra línea][carga] · [procedimiento del proyecto][skill].

## Fuentes y condiciones de uso

Consulta del **26/11/2026**. Para la futura carga, archivar los originales que se utilicen y su versión. Los puntos proyectados, longitudes medidas e IDs propuestos son resultados del estudio.

| Editor y edición | Cobertura empleada | Licencia o condiciones |
|---|---|---|
| Adif, [DR 2026][dr] y Adif AV, [DR 2026, eje 16][dr-av] y [mapas 3 y 4 de febrero de 2026][mapas] | Líneas 188 y 190, ancho y tensión del acceso AV, velocidad y sistemas de la 120. Las láminas esquemáticas dan valores de corredor | Consulta pública, © Adif y Adif AV |
| Adif, [estrategia de capacidad 2028, diciembre de 2024, tabla L120][cap] y [nota de energía de 09/05/2025][energia] | Vía general, frontera de tensión, máxima, excepción Golosa–Campillo y ámbito del proyecto energético | Consulta pública, © Adif. PDF de estrategia distribuido por RailNetEurope |
| Adif, [pliego LiDAR, lámina de ámbitos de mantenimiento «Salamanca», p. 52][esquema], [expediente de 2024 en el BOE][expediente]. Ministerio de Fomento, [informe anual 2015][informe] | PK de estaciones y bifurcación, numeración de los ejes y sistemas en servicio al abrir la 188 | Fuentes de consulta pública. Sin licencia abierta identificada para reproducir los esquemas |
| Adif, [Medina convencional][adif-conv], [Medina AV][adif-av] y [Salamanca][sal] | Identidad de estación y muestras de vía anunciada en días concretos. Los paneles cambian | Consulta pública, © Adif |
| Colaboradores de OpenStreetMap, [6016262][r120], [20685324][ida] y [20685325][vuelta] | Topología por nodos, vías y andenes alternativos, anchos, velocidades etiquetadas y longitudes medidas. Conservar versiones de los miembros al archivar la geometría | [ODbL 1.0 con atribución][odbl] |
| Renfe Viajeros, [GTFS AV/LD/MD][gtfs], [copias del 08, 12 y 17/11/2026][zips] | Paradas, horas, permisos, números, productos y días programados. El registro de Oniel documenta las ediciones y demás operadores de control | [CC BY 4.0][ccby] |
| Oniel, [base revisada][base], [plan de Ávila][plan-avila] e [incidencia #316][avila] | Ejes existentes, accesos propuestos y controles cruzados | Documentación y datos del proyecto con la procedencia indicada en su [registro][fuentes] |

[tarea]: https://github.com/ebotiab/Oniel/issues/320
[base]: https://github.com/ebotiab/Oniel/tree/9d3679bda5fd689d07bd89ea57d4b41d540d92e8
[avila]: https://github.com/ebotiab/Oniel/issues/316
[grisen]: https://github.com/ebotiab/Oniel/issues/310
[pr-avila]: https://github.com/ebotiab/Oniel/pull/317
[pio]: https://github.com/ebotiab/Oniel/pull/315
[plan-avila]: linea-avila-salamanca.md
[conv]: ../../backend/data/curated/madrid-avila-valladolid.json
[lav]: ../../backend/data/curated/lav-olmedo-ourense.json
[fuentes]: ../../backend/data/curated/sources.json
[zips]: ../../backend/data/raw/renfe
[costuras]: ../datos.md#las-costuras-entre-líneas
[atributos]: ../datos.md#atributos-de-tramo
[conjuntos]: ../datos.md#conjuntos-de-datos
[carga]: ../datos.md#añadir-otra-línea
[skill]: ../../.claude/skills/anadir-linea/SKILL.md
[variantes]: ../../backend/src/oniel/gtfs/variants.py
[paridad]: ../../frontend/e2e/rutas.spec.ts
[e2e]: ../../frontend/e2e/principe-pio.spec.ts
[dr]: https://www.adif.es/documents/20124/45113726/20250613_01_DR_Adif_Libro_2026.pdf/b74bbb86-ddd0-bdf7-d976-18cab630f2df
[dr-av]: https://www.adifaltavelocidad.es/documents/34745/51134530/20260227_01%2BDR%2BAdif_AV%2B2026_Libro.pdf/60f60247-935c-6d14-3ac4-8886c5e74dd6?t=1772454129932
[mapas]: ../../backend/data/raw/adif/dr-adif-av-2026-mapas_2026-11-12.pdf
[cap]: https://rne.eu/wp-content/uploads/ADIF-Capacity-Strategy-2028.pdf
[energia]: https://www.adif.es/w/adif-mantenimiento-instalaciones-energia-linea-medina-salamanca-fuentes-o%C3%B1oro
[esquema]: https://attachments.tender-service.com/07/1653/165392442_860937cbc64391e786890c9dbcec430b/DOC20240624111343PliegoDePrescripcionesTecnicas.PDF#page=52
[expediente]: https://www.boe.es/diario_boe/txt.php?id=BOE-B-2024-24013
[informe]: https://publicaciones.transportes.gob.es/downloadcustom/sample/1326
[adif-conv]: https://www.adif.es/w/10500-medina-del-campo
[adif-av]: https://www.adif.es/w/08240-medina-campo-av
[sal]: https://www.adif.es/w/30100-salamanca
[r120]: https://www.openstreetmap.org/relation/6016262
[ida]: https://www.openstreetmap.org/relation/20685324
[vuelta]: https://www.openstreetmap.org/relation/20685325
[odbl]: https://www.openstreetmap.org/copyright
[gtfs]: https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia
[ccby]: https://creativecommons.org/licenses/by/4.0/
