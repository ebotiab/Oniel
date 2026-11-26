# Horarios de SNCF entre París y Barcelona

Desde #230, Oniel incorpora los TGV de SNCF Voyageurs en la alta velocidad Barcelona–Girona–Figueres. No añade infraestructura francesa. La sección internacional sigue figurando como conexión no cargada.

## Fuente y extracto del 26 de noviembre de 2026

Se comprobó el [catálogo oficial francés](https://transport.data.gouv.fr/datasets/horaires-sncf), que enlaza el GTFS de SNCF y declara **ODbL 1.0**, con su [licencia](https://opendatacommons.org/licenses/odbl/1.0/). La fuente `sncf-horarios-abiertos` cita SNCF Voyageurs y el punto de acceso nacional; la cobertura muestra esa atribución y licencia con el diseño existente. El extracto se redistribuye bajo esa misma licencia en `backend/data/raw/sncf/`, con las filas originales, y este procedimiento permite reproducirlo. No se cambia la licencia de las otras fuentes.

El original, `Export_OpenData_SNCF_GTFS_NewTripId.zip`, se descargó el **26/11/2026 a las 08:57:56 UTC (09:57:56 CET)**. Su cabecera `Last-Modified` indica 25/11/2026 a las 20:57:08 UTC. Pesa **5.544.385 bytes** comprimido y **98.783.268 bytes** sin comprimir, de los que 83.103.658 son `stop_times.txt`. SHA-256: `e05ea39f6e49db54d2a63e16659cbfa98141c2e8936d56b90741dc3eb86911b9`. El [archivo histórico oficial fechado](https://transport-data-gouv-fr-resource-history-prod.cellar-c2.services.clever-cloud.com/83582/83582.20261126.002511.551839.zip) se descargó también: coincide exactamente en tamaño y huella. El ZIP nacional no se incorpora al repositorio ni se procesa al arrancar Render.

`gtfs_sncf_paris_espagne_2026-11-26.json` conserva procedencia, fecha, cabeceras, URL estable, huellas, tamaño y criterio. El script `backend/src/oniel/gtfs/sncf_extract.py` selecciona la ruta cuyo `route_long_name` es exactamente **Paris - Espagne TGV**; exige una única coincidencia y conserva todos sus viajes, todas sus paradas de viaje, calendarios, paradas y padres, agencia, metadatos y las demás referencias aplicables. Conserva también tablas vacías. Rechaza tablas desconocidas para revisar un cambio de esquema antes de renovar. El ZIP de salida es determinista.

| Tabla | Filas del extracto |
|---|---:|
| agency.txt | 1 |
| routes.txt | 1 |
| trips.txt | 63 |
| stop_times.txt | 656 |
| calendar_dates.txt | 614 |
| stops.txt | 28 (14 paradas y 14 estaciones padre) |
| feed_info.txt | 1 |
| transfers.txt | 0 |

El extracto pesa **8.347 bytes**, el **0,15 %** del ZIP nacional. SHA-256: `8289a8a77d47e8a3712a4abf571fd929b465d2f4fc7064fd4d0ace85f2e41519`. El original solo usa `calendar_dates.txt`: no se fabrica un calendario semanal. Su validez efectiva es **25/11/2026–30/04/2027**; los 63 viajes son variantes de calendario de seis números comerciales, con **614 trenes-día** y ninguno duplicado por número y fecha. El 26 y el 27 de noviembre circulan **9706, 9708, 9713 y 9715**, dos por sentido.

## Lectura, paradas y límite

Se reutilizan las opciones de `feeds`: `product: "TGV"`, `stop_id_prefix: "StopPoint:OCETGV INOUI-"`, `names_stops: false` y estos alias explícitos, contrastados con nombres y coordenadas del original y los nodos existentes. No se aplica una regla de recorte del dígito de control a todos los códigos.

| Código después del prefijo | Código de Oniel | Estación |
|---|---|---|
| 71718010 | 71801 | Barcelona-Sants |
| 71793000 | 79300 | Girona |
| 71043075 | 04307 | Figueres-Vilafant |

`train_number_field: "trip_headsign"` declara dónde publica SNCF el número comercial. Los otros feeds conservan `trip_short_name`: no se interpreta un destino cualquiera como número de tren. Los nombres de las estaciones españolas siguen siendo los que ya usa Oniel.

Los once códigos franceses permanecen diferenciados y se asignan como salidas por `limite-seccion-internacional`, sin `via` ni nuevos nodos. Sus nombres siguen disponibles como destinos externos. Todos los TGV seleccionados recorren los siete tramos de la línea, y ninguno se asigna a la convencional de Portbou ni a otra línea. No se solapan con los AVE internacionales de Renfe.

Se conservan `pickup_type` y `drop_off_type`: en las tres estaciones españolas el TGV hacia Francia permite subir pero no bajar; el de regreso permite bajar pero no subir. Cuenta como tren que pasa y para, pero no se ofrece como conexión comercial Barcelona–Girona–Figueres. La estimación del último tramo usa el mismo límite y criterio que los internacionales de Renfe.

## Renovación manual reproducible

El recordatorio semanal `oniel-data refresh expiring` ya incluye todas las fuentes salvo la de Renfe, que se refresca automáticamente. Por ello avisará de SNCF cuando queden 21 días o menos; no se amplía la automatización en esta entrega. #282 sigue abierta para el relevo de Ouigo, cuya cobertura termina el 12/12/2026: incorporar SNCF no alarga esa cobertura.

1. Revisar `AGENTS.md`, la skill `refresco-gtfs`, las PR de datos y el catálogo oficial. Comprobar licencia y URL GTFS actuales. No iniciar otra actualización de datos si hay una en curso.
2. Descargar el original fuera del repositorio y registrar la fecha real y su huella. Desde `backend/`, este ejemplo obtiene el fichero publicado; cambiar la URL si el catálogo oficial la ha sustituido:

```bash
uv run python - <<'PY'
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path

url = 'https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip'
with urllib.request.urlopen(url, timeout=60) as response:
    content = response.read()
    provenance = {
        'url': url,
        'downloaded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'sha256': hashlib.sha256(content).hexdigest(),
        'size_bytes': len(content),
        'last_modified': response.headers.get('Last-Modified'),
        'etag': response.headers.get('ETag'),
    }
Path('/tmp/sncf-original.zip').write_bytes(content)
Path('/tmp/sncf-procedencia.json').write_text(json.dumps(provenance, indent=2))
PY
uv run python -m oniel.gtfs.sncf_extract \
  --original /tmp/sncf-original.zip \
  --provenance /tmp/sncf-procedencia.json \
  --output data/raw/sncf/gtfs_sncf_paris_espagne_AAAA-MM-DD.zip
```

Sustituir `AAAA-MM-DD` por la fecha real. Si el catálogo ofrece un archivo histórico para esa versión, comprobar su SHA-256 y añadir su URL como `archive_url` al JSON de procedencia antes de extraer. Para reproducir la entrega del 26/11, descargar su URL histórica, verificar la huella indicada y usar como procedencia el objeto `original` del manifiesto conservado: el extracto debe tener exactamente la huella de arriba.

3. Comprobar las tablas y calendarios reales, no copiar los recuentos de esta entrega. Revisar nuevos códigos, destinos, restricciones y la ausencia de duplicados por número y día. Comparar los servicios con los otros feeds. Conservar el ZIP y el manifiesto juntos, sin modificar después sus filas. Si cambia la ruta o el formato, revisar el extractor y sus pruebas antes de declararlo.
4. Añadir la descarga al final de `feeds`, copiando las opciones de lectura anteriores; mantener el histórico. Actualizar `file`, fecha, cobertura y notas de `sncf-horarios-abiertos`, sus asignaciones si procede y la documentación. El código de importación no descarga ni extrae nada.
5. Pasar las comprobaciones rápidas, `pytest` con PostgreSQL y `oniel-data validate`. Con `main` integrado, ejecutar una sola vez `oniel-data import all`, medir el coste, revisar el nuevo día de referencia y sus recuentos, y pasar las pruebas del visor afectadas. La prueba del fichero de esta entrega queda fijada a su nombre, como las de Renfe y Ouigo.
6. Publicar mediante PR, esperar el CI y la fusión; verificar commit, importación y ausencia de errores con `oniel-data obs estado --verificar --commit <SHA> --esperar 15`, y las fichas/API en producción según `AGENTS.md`.
