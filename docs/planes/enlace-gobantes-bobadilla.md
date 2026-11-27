# Gobantes–Bobadilla, el recorrido directo Málaga–Granada

Los Avant de Málaga a Granada paran en **Antequera AV**, junto al casco urbano, y en **Loja**. Desde Málaga dejan la línea de Córdoba en Gobantes y se incorporan a la de Granada en Bobadilla. Así evitan **Antequera-Santa Ana**, la estación al oeste de Antequera. Oniel ya tiene los trenes y las dos bifurcaciones. Al redactar este plan faltaba el tramo entre ellas. La carga de la [incidencia #328][carga] siguió a la de [El Chaparral][turno].

## Resultado de la carga

La 014 se puede recorrer en ambos sentidos. Los seis Avant del 20/11/2026 tienen un paso estimado cada uno y el 08275 conserva su entrada por Santa Ana. Las medidas y el cotejo por edición están en [Cómo se cargó el enlace de Gobantes a Bobadilla](../datos.md#cómo-se-cargó-el-enlace-de-gobantes-a-bobadilla). Los apartados siguientes conservan el diagnóstico previo a la carga.

## Qué ofrecía el comparador

Consulta del 27/11/2026 con la red de [`main` en `bc8c4414`][base], sin cierres ni vías supuestas, sin límite de cambios de línea y con `max_ratio=2`. Tanto el visor estático como `GET /api/routes` devuelven **un solo recorrido por sentido**, con 12 tramos y sin inversión de marcha indicada. El visor lo titula «Por Antequera-Santa Ana». La instantánea muestra el horario del **11/12/2026**, su día de referencia. [Abrir Málaga → Granada][ida] · [Abrir Granada → Málaga][vuelta]

| Sentido | Camino que ofrece el grafo | Avant directos en el horario | Asignados a ese camino |
| --- | --- | --- | --- |
| Málaga-María Zambrano → Granada | 171,9 km, 50 min sin paradas | 08815, 08835, 08855 | 0 de 3 |
| Granada → Málaga-María Zambrano | 171,9 km, 50 min sin paradas | 08915, 08935, 08955 | 0 de 3 |

Desde Málaga el grafo pasa por Los Prados, Álora, **Gobantes → Antequera-Santa Ana → Bobadilla → Antequera AV**, Archidona, Riofrío, Loja, Tocón y La Chana antes de llegar a Granada. Desde Granada recorre esos nodos en orden inverso. Son 57,8 km de la línea de Málaga y 114,1 de la de Granada. Solo entre las bifurcaciones representa 15,8 km por Santa Ana (6,770 + 8,981). En la especificación de Granada, `enlace-malaga-granada` es una única `connection` en estado `no_cargada`, declarada de Bobadilla a Gobantes con un texto para cada sentido. Se ve a trazos en las dos fichas. El grafo solo recorre los tramos disponibles. [Especificación de Granada][granada] · [Antecedente #283][costuras]

Para repetir la tabla desde la raíz del commit de referencia, con Node 24, esta consulta usa el grafo, las paradas y los pasos por tramo que lee el panel del visor.

```sh
node --input-type=module <<'JS'
import { readFileSync } from 'node:fs'
import { composeNetwork } from './frontend/src/data/network.ts'
import { buildGraph } from './frontend/src/routing/graph.ts'
import { compararRecorridos, trenesDirectos, trenesDelRecorrido } from './frontend/src/app/recorridos.ts'

const leer = ruta => JSON.parse(readFileSync('frontend/public/data/' + ruta + '.json', 'utf8'))
const red = composeNetwork(leer('index'), {})
const grafo = buildGraph(red)
const malaga = 'malaga-maria-zambrano'
for (const [desde, hasta] of [[malaga, 'granada'], ['granada', malaga]]) {
  const origen = leer('nodes/' + desde)
  const trenes = trenesDirectos(origen.calls, leer('nodes/' + hasta).calls)
  for (const r of compararRecorridos(grafo, red, desde, hasta, new Map()).recorridos) {
    const pasos = new Map(r.tramosClave.map(id => {
      const tramo = leer('segments/' + id.replaceAll(':', '--'))
      return [id, new Set(tramo.passes.map(p => p.service.id))]
    }))
    console.log(desde, hasta, r.titulo, r.route.length_km, r.route.time_min, r.route.node_ids,
      r.route.reverse_node_ids, origen.date, trenes.map(t => t.train_number),
      trenesDelRecorrido(r, trenes, pasos).map(t => t.train_number))
  }
}
JS
```

La consulta equivalente a la API se puede repetir en los dos sentidos. Para probar una importación local, cambiar `api` por su URL local. [API de ida][api-ida] · [API de vuelta][api-vuelta]

```sh
api=https://oniel-api-5e63.onrender.com/api
for par in 'from=malaga-maria-zambrano&to=granada' 'from=granada&to=malaga-maria-zambrano'; do
  curl -fsS "$api/routes?$par&max_ratio=2" |
    jq '.routes[] | {length_km, time_min, node_ids, segment_ids, reverse_node_ids}'
done
```

## Qué vía falta y dónde empalma

Adif inventaría **8,6 km de línea 014** entre Bif. Gobantes y Bif. Bobadilla. Su declaración de 2019 ya recogía la conexión entre las líneas 030 y 036 entre los tramos puestos en servicio. El primer viaje directo de viajeros se hizo el 4 de abril de 2022. Renfe confirmó la recuperación de los seis servicios Avant diarios el 30 de abril de 2026 tras el corte de Álora. La fecha exacta de apertura técnica de la 014 queda pendiente. Desde la apertura de Antequera AV el 25 de enero de 2023, tanto el Avant Granada–Málaga como el Granada–Sevilla paran en la estación urbana. [Adif, anexo H de 2026][dr26] · [Adif, 2019, p. 66][dr19] · [Primer viaje del directo][apertura] · [Restablecimiento de Renfe][renfe26] · [Informe de la Administración del Estado de 2023][estacion]

| Parte del directo desde Málaga | Qué se reutiliza o incorpora |
| --- | --- |
| Málaga-María Zambrano → Los Prados → Álora → Gobantes | Tres tramos de `lav-cordoba-malaga` (030), en sentido decreciente, 51,024 km. El nodo `bif-gobantes` ya cae sobre la aguja OSM `2258256210` (longitud −4,7235031, latitud 37,0106686), compartida con la vía `1200950762` de la 030. |
| Gobantes → Bobadilla | Un tramo nuevo entre `bif-gobantes` y `bif-bobadilla`, ambos compartidos. En la relación OSM `16228313` hay ocho vías contiguas entre las agujas, **8,857 km** en ambos sentidos. |
| Bobadilla → Antequera AV → Loja → Granada | Siete tramos de `lav-antequera-granada` (036), pasando por Archidona, Riofrío, Tocón y La Chana. La aguja OSM `4848128991` (−4,6409519, 37,0437736) es también vértice de la vía `218316743` de la 036. Desde esa aguja hasta Granada se miden 105,166 km. |

**Corte de Bobadilla.** La polilínea ya importada de la 036 pasa exactamente por la aguja, en su km geométrico 8,934. El corte curado está en el km 8,981, unos **47 m** más hacia Antequera AV. Se propone situar el mismo `bif-bobadilla` en la aguja en las dos especificaciones y conservar los ID de sus tramos vecinos. Así se cuenta esa vía una sola vez. La cifra histórica de 190 m en la documentación procede de otra comparación con el PK de referencia. Los 47 m salen de proyectar la aguja sobre la geometría que carga este commit. [Especificación de Málaga][malaga] · [Especificación de Granada][granada] · [Construcción de las dos líneas][antecedentes]

En el extracto del Avant, las vías OSM desde Gobantes son `492843108 → 492843098 → 591274874 → 591274873 → 591274875 → 492843097 → 492843105 → 492843093`. Cada una comparte su nodo final con la siguiente. Carecen de `ref=014`. Para repetir la medida con [el trazador de Oniel][trazador], usar `trace_osm_relation(raw, 16228313, gobantes, bobadilla)` con el JSON y las coordenadas de la tabla, en orden (longitud, latitud). Al invertir los extremos, `polyline.length_km` vuelve a dar **8,856662 km** y 86 vértices. La relación recoge un itinerario hacia Granada. Recorrer su geometría a la inversa comprueba la continuidad del eje. La vía concreta que usa cada circulación de vuelta queda sin determinar. Los 165,048 km que mide la relación completa del Avant concuerdan con la suma de los dos trechos reutilizados y el enlace, unos **165,0 km** entre capitales, casi siete menos que por Santa Ana. [Original del Avant][osm-avant] · [Original de la 030][osm-030] · [Original de la 036][osm-036]

| Atributo | Evidencia y dato que se puede cargar |
| --- | --- |
| Vías, ancho y alimentación | Adif describe doble vía, ancho estándar de 1.435 mm y electrificación a 2 × 25 kV, 50 Hz. Las ocho vías OSM llevan `tracks=2`, `gauge=1435`, `voltage=25000` y `frequency=50`. En el visor corresponde «25 kV 50 Hz». [Declaración de Adif][dr19] · [Mapas archivados, mapa 3][mapas] |
| Velocidad y señalización | Las ocho vías OSM llevan `maxspeed=220` km/h y `railway:etcs=2`. El mapa 3 rotula 220 en el enlace. Adif documenta ERTMS nivel 2, bloqueo de control automático (BCA), control de tráfico centralizado (CTC) y radio GSM-R en la 014. Queda por acreditar cualquier respaldo ASFA específico del enlace. [OSM][osm-avant] · [Mapas 3 y 4][mapas] · [Adif, p. 66][dr19] |
| Puntos kilométricos (PK) | En la 036, Bobadilla tiene PK de referencia 105,753 en Oniel. El pliego de Adif usa 105+748. Para la 014 delimita el mantenimiento entre 0+300 y 9+000 en vía 3 y entre 0+340 y 8+960 en vía 4. Su tabla 3 da 103+594 **aproximado** para Gobantes bajo la 036. La correspondencia de esas referencias con cada aguja OSM y el PK exacto de Gobantes en la 030 quedan pendientes. Mantener el PK de referencia de la 036 separado del kilometraje propio del enlace. Dejar sin `reference_pk_km` los extremos de la 014 hasta justificar vía y origen. [Pliego, lote 3 y tabla 3][pliego] · [Referencia curada][granada] |

## Qué trenes deben pasar por el enlace

**Viernes 20/11/2026**, hora peninsular, edición Renfe del **17/11**, vigente del 16/11/2026 al 29/09/2027. Se cruzaron `trips.txt` y `stop_times.txt` con `calendar.txt` y las altas y bajas de `calendar_dates.txt`. En el horario, `54413` es Málaga-María Zambrano, `02030` Antequera AV, `02003` Antequera-Santa Ana, `05012` Loja y `05000` Granada. La API devolvió los mismos códigos, horas y permisos para los tres `trip_id`. [GTFS archivado][gtfs] · [Recuentos de esa edición y fecha][historico]

| Tren y `trip_id` | Paradas comerciales en orden, con llegada–salida | Camino que contrasta |
| --- | --- | --- |
| Avant **08815** · `0881512026-11-16` | Málaga-María Zambrano 09:20 → **Antequera AV 09:46–09:48** → Loja 10:14–10:16 → Granada 10:43 | 83 min. Gobantes → Bobadilla entre Málaga y Antequera AV. |
| Avant **08915** · `0891512026-11-16` | Granada 07:36 → Loja 07:56–07:58 → **Antequera AV 08:25–08:27** → Málaga-María Zambrano 09:05 | 89 min. Bobadilla → Gobantes entre Antequera AV y Málaga. |
| Avant **08275** · `0827512026-11-16` | Sevilla-Santa Justa 07:40 → Córdoba-Julio Anguita 08:24–08:29 → Puente Genil-Herrera 08:57–08:58 → **Antequera-Santa Ana 09:16–09:20** → **Antequera AV 09:28–09:30** → Loja 09:56–09:58 → Granada 10:25 | Entra desde Córdoba por Santa Ana y sigue por Bobadilla hacia Antequera AV. Cero pasos por Gobantes y la 014. |

En los tres viajes se permite solo subir en origen, subir y bajar en las paradas intermedias y solo bajar en destino. Gobantes y Bobadilla son bifurcaciones sin parada comercial. Los otros cuatro directos de la tabla inicial también circulan el 20/11. La coincidencia de sus paradas con el itinerario público permite asignar ese patrón al enlace. El GTFS publica horas en las estaciones. Las horas en las agujas serán **estimadas**. Cualquier otro patrón que no se pueda contrastar queda pendiente de asignación.

Para repetir el cotejo con el lector de Oniel desde `backend/`, basta este comando. La fecha en el `trip_id` identifica una ventana del fichero. El calendario determina si circula el día elegido.

```sh
uv run python - <<'PY'
from datetime import date
from pathlib import Path
from oniel.gtfs.reader import read_feed

feed = read_feed(Path("data/raw/renfe/google_transit_av_ld_md_2026-11-17.zip"))
def hora(segundos):
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}"

for tren in feed.trips.values():
    if date(2026, 11, 20) not in feed.service_dates[tren.service_id]:
        continue
    if {"54413", "05000"} <= feed.stop_ids_of(tren) or tren.train_number == "08275":
        print(tren.train_number, tren.trip_id,
              [(p.stop_id, hora(p.arrival_s), hora(p.departure_s), p.pickup_type, p.drop_off_type)
               for p in tren.stop_times])
PY
```

## Archivos y criterios de aceptación de la carga

1. **Geometría y procedencia.** Crear `backend/data/curated/enlace-gobantes-bobadilla.json`, propuesto como `link_of: lav-antequera-granada`, en Andalucía. Ahí está hoy el trazo. Registrar la especificación tras sus dos líneas en `backend/src/oniel/settings.py`. Reutilizar ambas bifurcaciones con `shared: true`. Retirar `enlace-malaga-granada` de la 036 y comprobar en las dos fichas el enlace navegable. Ajustar el corte en Bobadilla, comprobar extremos coincidentes y que continúan los tres tramos de Málaga y los siete de Granada con sus identificadores. Ampliar la cobertura de los originales en [`sources.json`][fuentes] y registrar los documentos nuevos, con licencia, consulta y copia o ficha fechada en `backend/data/raw/`.
2. **Asignación por paradas.** En la [030][malaga], la regla `malaga-granada-por-gobantes` reconoce `54413` y `02030` consecutivas en ambos órdenes. Para ese patrón, encadenar desde Gobantes la 014 y desde Bobadilla la 036 hacia `02030`, `05012` y `05000`. En la [036][granada], `54413` sale por Bobadilla y seguirá por la 014 y la 030. El enlace tendrá su propio filtro y asignaciones de salida a cada lado. Comprobar que los seleccionados son exactamente los del patrón observado `54413 → 02030 → 05012 → 05000` o su inverso. Conservar las asignaciones ordinarias por `02003` para quienes llegan de Córdoba. Un filtro que acepte cualquier Avant o cualquier tren que omita Santa Ana incorporaría servicios ajenos.
3. **Identidad, paradas y pasos.** Para cada ZIP del 08, 12 y 17/11, comparar antes y después el conjunto de `(operador, número, fecha)` dentro de la edición y exigir una sola fila por identidad al unir `services` y `service_dates`. Comparar también `(seq, stop_id, arrival_s, departure_s, pickup_type, drop_off_type)`. Repetir `GET /api/services/{trip_id}?date=2026-11-20` para los tres ejemplos. Cruzar `service_segment_passes` con los servicios del día. Cada uno de los seis directos debe sumar un solo paso por la 014, en su sentido, entre las horas de Málaga y Antequera AV. Debe conservar sus otros diez pasos y tener cero en los dos brazos de Santa Ana. El 08275 conserva el paso Santa Ana–Bobadilla. Exigir unicidad de `(dataset_id, service_id, segment_id)` y cero pasos indeterminados. Para Renfe el 20/11, se esperan **6 en la 014**, **49** en cada uno de los tres tramos de Málaga frente a **43** en Gobantes–Santa Ana, y **24** en cada uno de los siete de Granada frente a **18** en Santa Ana–Bobadilla. Contrastar identidades además de totales. [Histórico del 20/11][historico] · [Pruebas existentes de las dos líneas][pruebas]
4. **Comparador y control.** Con el mismo `main`, importación, escenario y límites, comparar en la API y en el visor estático la lista ordenada de rutas, sus `node_ids`, `segment_ids`, `reverse_node_ids`, kilómetros a la décima y minutos teóricos. El directo debe medir unos **165,0 km** en ambos sentidos, seguir desde Málaga la secuencia Gobantes → Bobadilla → **Antequera AV** → Loja y evitar Santa Ana sin invertir la marcha. Una prueba en memoria con los extremos medidos y 220 km/h dio **165,0 km y 49 min**. Conservar el camino de Córdoba a Granada por Santa Ana para el control. Al consultar las paradas en ambas estaciones, solo los trenes con parada comercial deben aparecer. En la fecha de referencia de la instantánea, comprobar que los tres directos de cada sentido quedan asignados una sola vez al recorrido correcto y que desaparece para ellos el aviso de vía sin cargar.
5. **Verificación y publicación.** Incluir la nueva especificación en `backend/tests/conftest.py` y ampliar `backend/tests/test_lav_cordoba_granada.py`, `test_routing.py` y las pruebas de integración y unicidad. Cubrir la paridad en `frontend/e2e/fixtures/rutas-paridad.json` y `frontend/e2e/rutas.spec.ts`, y el comportamiento visible en `frontend/e2e/malaga.spec.ts` y `costuras.spec.ts`. Desde `backend/`, validar la especificación y la red con `uv run oniel-data validate`, importar en una base vacía con `uv run oniel-data import all` y revisar `frontend/public/data/`, los recuentos de `docs/datos.md`, `docs/simulacion.md` y `AGENTS.md`. Pasar pytest, Playwright estático y la integración con la API local. La PR de datos podrá cerrar [#328][carga] tras el turno de [#323][turno]. [Procedimiento del repositorio][procedimiento]

## Fuentes y condiciones de uso

Consulta documental del 27/11/2026. Para reproducir las medidas y los horarios se usan las copias fechadas del repositorio.

| Editor | Material y condiciones |
| --- | --- |
| Adif y Adif Alta Velocidad | [Declaración de 2019, p. 66][dr19], [Declaración de 2026, anexo H][dr26], [mapas archivados el 12/11/2026][mapas] (`adif-declaracion-red-2026-mapas`) y [pliego oficial de mantenimiento, lote 3][pliego]. Consulta pública, © sus editores. Citar los hechos y las páginas de procedencia. |
| Colaboradores de OpenStreetMap | Extractos del 12/11/2026 de las relaciones [11143233][osm-030], [2869549][osm-036] y [16228313][osm-avant], registrados como `osm-relation-<número>`. Geometría y etiquetas bajo ODbL 1.0, con atribución a los colaboradores de OpenStreetMap. |
| Renfe Viajeros | [GTFS AV/LD/MD del 17/11/2026][gtfs], fuente `renfe-gtfs-av-ld-md`, CC BY 4.0 con atribución a Renfe Viajeros. El [catálogo de Renfe Data][portal] mantiene la ficha del conjunto. El [aviso del 29/04/2026][renfe26] es de consulta pública, © Renfe. |
| Junta de Andalucía y Administración General del Estado | [Primer viaje del directo, 04/04/2022][apertura] e [informe de evaluación de 2023, apartado de Renfe][estacion]. Publicaciones institucionales de consulta pública. |
| Colaboradores de Wikipedia | La referencia ya registrada `wikipedia-lav-antequera-granada` (revisión 169316239, 03/09/2025, CC BY-SA 4.0) explica la procedencia del PK 105,753 que hoy usa la 036. [Registro y notas de la edición][fuentes] |

[carga]: https://github.com/ebotiab/Oniel/issues/328
[turno]: https://github.com/ebotiab/Oniel/issues/323
[base]: https://github.com/ebotiab/Oniel/tree/bc8c4414d0c863cc5860c1abaa73f71ec1217201
[ida]: https://oniel.vercel.app/recorridos/malaga-maria-zambrano/granada
[vuelta]: https://oniel.vercel.app/recorridos/granada/malaga-maria-zambrano
[api-ida]: https://oniel-api-5e63.onrender.com/api/routes?from=malaga-maria-zambrano&to=granada&max_ratio=2
[api-vuelta]: https://oniel-api-5e63.onrender.com/api/routes?from=granada&to=malaga-maria-zambrano&max_ratio=2
[costuras]: https://github.com/ebotiab/Oniel/pull/283
[malaga]: ../../backend/data/curated/lav-cordoba-malaga.json
[granada]: ../../backend/data/curated/lav-antequera-granada.json
[antecedentes]: ../datos.md#cómo-se-construyeron-las-líneas-de-alta-velocidad-córdobamálaga-y-antequeragranada
[procedimiento]: ../datos.md#añadir-otra-línea
[trazador]: ../../backend/src/oniel/network/build.py
[osm-030]: ../../backend/data/raw/osm/relation_11143233_lav_cordoba_malaga_2026-11-12.json
[osm-036]: ../../backend/data/raw/osm/relation_2869549_lav_antequera_granada_2026-11-12.json
[osm-avant]: ../../backend/data/raw/osm/relation_16228313_avant_malaga_granada_2026-11-12.json
[mapas]: ../../backend/data/raw/adif/dr-adif-av-2026-mapas_2026-11-12.pdf
[fuentes]: ../../backend/data/curated/sources.json
[gtfs]: ../../backend/data/raw/renfe/google_transit_av_ld_md_2026-11-17.zip
[historico]: ../../frontend/public/data/historico/renfe-gtfs-av-ld-md-2026-11-17/segment-counts.json
[pruebas]: ../../backend/tests/test_lav_cordoba_granada.py
[dr19]: https://www.adifaltavelocidad.es/documents/34745/7247882/DR_ADIF_AV_V1_20191.pdf/c5b189a9-0192-dd89-2bfe-171a37a9a20f?t=1647948841767
[dr26]: https://www.adifaltavelocidad.es/documents/34745/51134530/20260227_01%2BDR%2BAdif_AV%2B2026_Libro.pdf/60f60247-935c-6d14-3ac4-8886c5e74dd6?t=1772454129932
[pliego]: https://contrataciondelestado.es/wps/wcm/connect/5b2b94b2-01ca-4f0d-b4f8-28d072990258/DOC20230306124050PliegoDePrescripcionesTecnicas.PDF?MOD=AJPERES
[apertura]: https://www.juntadeandalucia.es/organismos/sobre-junta/altos-cargos/agenda/detalle/170830.html
[portal]: https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia
[renfe26]: https://grupo.renfe.com/es/es/sala-de-prensa/noticias/2026/04/renfe-ofrece-primer-ave-directo-madrid-malaga
[estacion]: https://mptmd.gob.es/content/dam/mpt/delegaciones_gobierno/informe-evaluacion/Indice_informe-evaluacion2023/5_TRANSPORTES_Y_MOVILIDAD_SOSTENIBLE_2023.pdf
