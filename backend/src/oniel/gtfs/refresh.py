"""Refresco de un fichero de horarios: descargar el publicado, compararlo y declararlo si cambió.

Lo usa el flujo `.github/workflows/gtfs.yml` y puede ejecutarse a mano (`oniel-data refresh gtfs`).
No toca la base de datos: deja el zip nuevo en ``data/raw/``, lo añade a ``feeds`` de
``sources.json`` y pone al día la fuente y las tablas de ``docs/datos.md``. Después hay que
ejecutar ``validate`` e ``import all``, como con cualquier fichero añadido a mano. El fichero
anterior no se quita: cada descarga es un conjunto de datos más.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from oniel.gtfs.importer import file_sha256
from oniel.gtfs.reader import read_feed
from oniel.network.spec import FeedSpec, load_feeds

MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
DATE_IN_NAME = re.compile(r"\d{4}-\d{2}-\d{2}")
#: Frase de ``coverage`` de la fuente que dice qué días cubre el fichero vigente.
VALIDITY_SENTENCE = re.compile(r"Validez del fichero del [^.]*\.")
#: Frase de ``notes`` de la fuente que dice de cuándo es el fichero vigente.
PUBLISHED_SENTENCE = re.compile(r"Fichero ([\w.-]+) (?:publicado|descargado) el [^.]*\.")


def spanish_date(day: dt.date) -> str:
    return f"{day.day} de {MONTHS[day.month - 1]} de {day.year}"


def spanish_range(start: dt.date, end: dt.date) -> str:
    """«del 7 de noviembre de 2026 al 29 de septiembre de 2027»; el año no se repite si coincide."""
    first = (
        spanish_date(start) if start.year != end.year else spanish_date(start).rsplit(" de ", 1)[0]
    )
    return f"del {first} al {spanish_date(end)}"


def content_sha256(path: Path) -> str:
    """SHA-256 del contenido de un zip: los nombres y los bytes de sus ficheros, ya descomprimidos.

    Renfe sirve su GTFS desde varios servidores y cada uno tiene su propio zip: el mismo horario
    llega con bytes distintos según cuál responda (medido el 12 de noviembre de 2026: tres SHA-256
    en cuatro descargas seguidas, con los siete ficheros de dentro idénticos). Comparar el zip
    daría por nuevo un horario que no lo es; se compara lo que lleva dentro.
    """
    digest = hashlib.sha256()
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            data = zf.read(name)
            digest.update(f"{name}\0{len(data)}\0".encode())
            digest.update(data)
    return digest.hexdigest()


def ckan_package_api(dataset_url: str) -> str | None:
    """Dirección de la API de CKAN para la página de un conjunto de datos, o ``None`` si no lo es.

    data.renfe.com es un portal CKAN: la página ``…/dataset/<nombre>`` registrada en
    ``sources.json`` tiene su ficha en ``…/api/3/action/package_show?id=<nombre>``, que enumera
    los ficheros publicados con su dirección de descarga.
    """
    parsed = urlparse(dataset_url)
    found = re.fullmatch(r"/dataset/([\w-]+)/?", parsed.path)
    if parsed.scheme != "https" or not found:
        return None
    return f"https://{parsed.netloc}/api/3/action/package_show?id={found.group(1)}"


def gtfs_resource_url(package: dict[str, Any]) -> str:
    """Dirección del fichero GTFS de la ficha CKAN de un conjunto de datos."""
    resources = package.get("result", {}).get("resources", [])
    urls = [
        str(r["url"])
        for r in resources
        if str(r.get("format", "")).upper() == "GTFS" or str(r.get("url", "")).endswith(".zip")
    ]
    if len(urls) != 1:
        raise ValueError(f"se esperaba un fichero GTFS en la ficha y hay {len(urls)}")
    return urls[0]


def download_feed(dataset_url: str, target: Path, *, timeout_s: float = 120.0) -> dt.date | None:
    """Descarga el GTFS publicado en la página de un conjunto de datos y lo deja en ``target``.

    Devuelve el día de publicación según la cabecera ``Last-Modified`` del servidor, si la da.
    Solo sabe descargar de portales CKAN sin sesión iniciada (el de Renfe); las fuentes que exigen
    una cuenta, como el Punto de Acceso Nacional, se descargan a mano.
    """
    api = ckan_package_api(dataset_url)
    if api is None:
        raise ValueError(f"{dataset_url} no es la página de un conjunto de datos de un portal CKAN")
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        package = client.get(api)
        package.raise_for_status()
        response = client.get(gtfs_resource_url(package.json()))
        response.raise_for_status()
        target.write_bytes(response.content)
    modified = response.headers.get("last-modified")
    return parsedate_to_datetime(modified).date() if modified else None


@dataclass
class RefreshResult:
    """Qué hizo el refresco de una fuente; se imprime como JSON para el flujo."""

    source_id: str
    changed: bool
    #: SHA-256 del zip descargado (el que guarda la tabla `datasets`) y de su contenido, que es
    #: el que se compara.
    sha256: str
    content_sha256: str
    #: Fichero vigente antes del refresco, relativo a ``data/``, y su conjunto de datos.
    previous_file: str
    previous_dataset_id: str
    #: Solo si cambió: el fichero guardado, su conjunto, su día de descarga y los días que cubre.
    file: str | None = None
    dataset_id: str | None = None
    retrieved_on: str | None = None
    #: El día de descarga como se escribe en un título: «12 de noviembre de 2026».
    retrieved_on_text: str | None = None
    published_on: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    #: Textos que el refresco no supo poner al día y tiene que mirar quien revise la PR.
    pending: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def dataset_id_of(feed: FeedSpec) -> str:
    return f"{feed.source_id}-{feed.retrieved_on.isoformat()}"


def refresh_source(
    downloaded: Path,
    *,
    source_id: str,
    sources_path: Path,
    data_dir: Path,
    today: dt.date,
    published_on: dt.date | None = None,
    docs_path: Path | None = None,
) -> RefreshResult:
    """Compara un fichero descargado con los declarados de su fuente y, si es nuevo, lo declara.

    Se compara el SHA-256 del contenido (`content_sha256`) con el de todos los ficheros de la
    fuente, no solo con el vigente: un horario que ya está no se vuelve a añadir. Si es nuevo, se copia a ``data/raw/`` con el día
    de descarga en el nombre, se añade al final de ``feeds`` con las mismas opciones de lectura
    que el anterior y se ponen al día ``file``, ``retrieved_on`` y las frases de validez y de
    publicación de la fuente.
    """
    declared = [f for f in load_feeds(sources_path) if f.source_id == source_id]
    if not declared:
        raise ValueError(f"la fuente {source_id} no tiene ningún fichero en feeds")
    current = declared[-1]
    content = content_sha256(downloaded)
    result = RefreshResult(
        source_id=source_id,
        changed=False,
        sha256=file_sha256(downloaded),
        content_sha256=content,
        previous_file=current.file,
        previous_dataset_id=dataset_id_of(current),
    )
    if any(content_sha256(data_dir / f.file) == content for f in declared):
        return result
    if current.retrieved_on >= today:
        raise ValueError(
            f"{current.file} ya es del {current.retrieved_on.isoformat()}: un fichero por fuente y día"
        )
    if not DATE_IN_NAME.search(current.file):
        raise ValueError(f"{current.file} no lleva la fecha en el nombre")
    # Leerlo entero antes de declararlo: si no es un GTFS legible, falla aquí y no se guarda nada.
    feed = read_feed(downloaded, stop_id_prefix=current.stop_id_prefix)
    new_file = DATE_IN_NAME.sub(today.isoformat(), current.file)
    shutil.copyfile(downloaded, data_dir / new_file)

    raw = json.loads(sources_path.read_text(encoding="utf-8"))
    entry = current.model_dump(mode="json", exclude_none=True)
    entry.update(file=new_file, retrieved_on=today.isoformat())
    raw["feeds"].append(entry)
    source = next(s for s in raw["sources"] if s["id"] == source_id)
    source["file"] = new_file
    source["retrieved_on"] = today.isoformat()
    validity = f"Validez del fichero {spanish_range(feed.feed_start, feed.feed_end)}."
    coverage, n = VALIDITY_SENTENCE.subn(validity, source.get("coverage") or "", count=1)
    if n:
        source["coverage"] = coverage
    else:
        result.pending.append(
            f"`coverage` de la fuente {source_id}: no dice la validez del fichero"
        )
    when = (
        f"publicado el {spanish_date(published_on)}"
        if published_on
        else f"descargado el {spanish_date(today)}"
    )
    notes, n = PUBLISHED_SENTENCE.subn(rf"Fichero \1 {when}.", source.get("notes") or "", count=1)
    if n:
        source["notes"] = notes
    else:
        result.pending.append(f"`notes` de la fuente {source_id}: no dice de cuándo es el fichero")
    sources_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result.changed = True
    result.file = new_file
    result.dataset_id = f"{source_id}-{today.isoformat()}"
    result.retrieved_on = today.isoformat()
    result.retrieved_on_text = spanish_date(today)
    result.published_on = published_on.isoformat() if published_on else None
    result.valid_from = feed.feed_start.isoformat()
    result.valid_to = feed.feed_end.isoformat()
    if docs_path is not None:
        result.pending.extend(
            update_docs(
                docs_path,
                source_id=source_id,
                dataset_id=result.dataset_id,
                previous_dataset_id=result.previous_dataset_id,
                retrieved_on=today,
                valid=(feed.feed_start, feed.feed_end),
            )
        )
    return result


def update_docs(
    docs_path: Path,
    *,
    source_id: str,
    dataset_id: str,
    previous_dataset_id: str,
    retrieved_on: dt.date,
    valid: tuple[dt.date, dt.date],
) -> list[str]:
    """Pone al día las dos tablas de ``docs/datos.md`` que nombran el fichero; devuelve lo que no pudo.

    En «Fuentes de esta versión» cambia la fecha de consulta de la fuente; en «Conjuntos de datos»
    añade la fila del conjunto nuevo debajo de la del anterior.
    """
    pending: list[str] = []
    lines = docs_path.read_text(encoding="utf-8").split("\n")
    source_row = next((i for i, x in enumerate(lines) if x.startswith(f"| `{source_id}` |")), None)
    if source_row is None:
        pending.append(f"`docs/datos.md`, «Fuentes de esta versión»: falta la fila de {source_id}")
    else:
        cells = lines[source_row].split(" | ")
        cells[-1] = f"{retrieved_on.isoformat()} |"
        lines[source_row] = " | ".join(cells)
    previous_row = next(
        (i for i, x in enumerate(lines) if x.startswith(f"| `{previous_dataset_id}` |")), None
    )
    if previous_row is None:
        pending.append(
            f"`docs/datos.md`, «Conjuntos de datos»: falta la fila de {previous_dataset_id}"
        )
    else:
        operator = lines[previous_row].split(" | ")[2]
        lines.insert(
            previous_row + 1,
            f"| `{dataset_id}` | `{source_id}` | {operator} | {retrieved_on.isoformat()}"
            f" | {spanish_range(*valid)} |",
        )
    docs_path.write_text("\n".join(lines), encoding="utf-8")
    return pending


def expiring_feeds(
    sources_path: Path, data_dir: Path, *, today: dt.date, days: int, exclude: frozenset[str]
) -> list[dict[str, Any]]:
    """Ficheros vigentes cuya validez termina en ``days`` días o menos (o ya terminó).

    Sirve para recordar las fuentes que no se refrescan solas (``exclude`` son las que sí): sus
    horarios dejan de valer un día concreto y hay que descargar el fichero siguiente antes.
    """
    current = {f.source_id: f for f in load_feeds(sources_path)}
    out: list[dict[str, Any]] = []
    for source_id, feed in current.items():
        if source_id in exclude:
            continue
        end = read_feed(data_dir / feed.file, stop_id_prefix=feed.stop_id_prefix).feed_end
        if (end - today).days <= days:
            out.append(
                {
                    "source_id": source_id,
                    "operator_id": feed.operator_id,
                    "file": feed.file,
                    "valid_to": end.isoformat(),
                    "valid_to_text": spanish_date(end),
                    "days_left": (end - today).days,
                }
            )
    return out


def _count_changes(previous: dict[str, Any], new: dict[str, Any]) -> list[str]:
    before: dict[str, int] = previous["counts"]
    after: dict[str, int] = new["counts"]
    rows = [
        f"| `{segment}` | {before.get(segment, 0)} | {after.get(segment, 0)} |"
        for segment in sorted(before.keys() | after.keys())
        if before.get(segment, 0) != after.get(segment, 0)
    ]
    same_day = previous["date"] == new["date"]
    days = (
        f"el {spanish_date(dt.date.fromisoformat(new['date']))}, día de referencia de los dos"
        if same_day
        else f"cada uno en su día de referencia: el {spanish_date(dt.date.fromisoformat(previous['date']))}"
        f" el anterior y el {spanish_date(dt.date.fromisoformat(new['date']))} el nuevo"
    )
    if not rows:
        return [f"Los pasos por tramo no cambian ({days})."]
    return [
        f"Pasos por tramo que cambian ({days}); los demás tramos quedan igual:",
        "",
        "| Tramo | Antes | Ahora |",
        "|---|---|---|",
        *rows,
    ]


def pr_body(result: dict[str, Any], import_report: dict[str, Any], snapshot_dir: Path) -> str:
    """Descripción de la PR del refresco: validez, viajes por línea y cambios en los pasos por tramo.

    ``result`` es la salida de `refresh gtfs`, ``import_report`` la de `import all`, y los pasos
    por tramo de cada conjunto se leen de ``historico/`` en la instantánea recién exportada.
    """
    by_dataset = {g["dataset"]["id"]: g for g in import_report["gtfs"]}
    # El conjunto nuevo se busca por su SHA-256: si la base ya tenía otro fichero de ese día, el
    # importador le habrá dado un id con sufijo.
    new = next(g for g in import_report["gtfs"] if g["dataset"]["sha256"] == result["sha256"])
    new_id: str = new["dataset"]["id"]
    previous = by_dataset.get(result["previous_dataset_id"])
    valid = spanish_range(
        dt.date.fromisoformat(result["valid_from"]), dt.date.fromisoformat(result["valid_to"])
    )
    retrieved = spanish_date(dt.date.fromisoformat(result["retrieved_on"]))
    published = (
        f", publicado el {spanish_date(dt.date.fromisoformat(result['published_on']))}"
        if result.get("published_on")
        else ""
    )
    out = [
        "## Qué cambia",
        "",
        f"Un fichero de horarios nuevo de la fuente `{result['source_id']}`, descargado el"
        f" {retrieved}{published}. Su contenido no coincide con el de ninguno de los ya declarados"
        f" (SHA-256 del contenido `{result['content_sha256'][:12]}…`).",
        "",
        f"- Fichero: `backend/data/{result['file']}`, conjunto de datos `{new_id}`.",
        f"- Validez: {valid}.",
        f"- El anterior, `{result['previous_dataset_id']}`, sigue declarado: refrescar añade un"
        " conjunto, no sustituye. Los días que cubren los dos los sirve el nuevo.",
        "- `sources.json` (`feeds`, y `file`, `retrieved_on`, cobertura y notas de la fuente),"
        " las tablas de `docs/datos.md` y la instantánea de `frontend/public/data` van al día.",
        "",
        "## Viajes por línea",
        "",
        "| Línea | Viajes antes | Viajes ahora |",
        "|---|---|---|",
    ]
    for line_id, line in new["lines"].items():
        before = previous["lines"].get(line_id, {}).get("trips", "–") if previous else "–"
        out.append(f"| `{line_id}` | {before} | {line['trips']} |")
    before_total = previous["trips_imported"] if previous else "–"
    out += [
        f"| Total importado (un viaje puede recorrer varias líneas) | {before_total} | {new['trips_imported']} |",
        "",
        f"El fichero trae {new['trips_in_feed']} viajes de toda España. Paradas sin asignar:"
        f" {len(new['unmapped_stops'])}.",
        "",
        "## Pasos por tramo",
        "",
    ]
    counts = [
        snapshot_dir / "historico" / dataset / "segment-counts.json"
        for dataset in (result["previous_dataset_id"], new_id)
    ]
    if all(p.exists() for p in counts):
        before_counts, after_counts = (json.loads(p.read_text(encoding="utf-8")) for p in counts)
        out += _count_changes(before_counts, after_counts)
    else:
        out.append("No se han podido comparar: falta el histórico de alguno de los dos conjuntos.")
    out += [
        "",
        "## Qué mirar al revisar",
        "",
        "- Que la validez y los viajes por línea tengan sentido: una caída grande en una línea"
        " puede ser un cambio real del servicio o una parada o un recorrido que el fichero nuevo"
        " nombra de otra forma.",
        "- La vista previa de Vercel de esta PR: el día de referencia, la cobertura y algún tramo.",
        "- En `docs/datos.md`, las frases que dicen «hoy» junto a una validez o un recuento: el"
        " flujo solo pone al día las tablas.",
    ]
    out += [f"- Sin actualizar, a mano: {item}." for item in result.get("pending", [])]
    out += [
        "",
        "## Comprobaciones",
        "",
        "Antes de abrir esta PR, el flujo ha pasado sobre estos mismos ficheros `oniel-data"
        " validate`, `oniel-data import all`, `pytest` y Playwright sobre la instantánea"
        " regenerada. Si alguna hubiera fallado no habría PR, sino una incidencia con la"
        " etiqueta `refresco-gtfs`.",
        "",
        "Los recuentos que comprueba `pytest` no cambian con un fichero nuevo: esas pruebas leen"
        " siempre los ficheros fijos de `backend/tests/conftest.py` (Renfe del 8 de noviembre de"
        " 2026 y Ouigo del 12 de noviembre de 2026). Las de Playwright sí leen la instantánea, y"
        " por eso se pasan antes de abrir la PR.",
        "",
        "GitHub retiene el CI de una PR que abre otro flujo: para que `Backend` y `Frontend`"
        " aparezcan abajo hay que pulsar «Approve workflows to run». El flujo lanza además el CI"
        " sobre esta rama; ese resultado está en la pestaña Actions y en la marca del commit.",
        "",
        "Si la PR entra en conflicto con `main` porque otra PR regeneró la instantánea, lo más"
        " sencillo es cerrarla sin fusionar, borrar su rama y lanzar «Refresco del GTFS» a mano.",
        "",
        "Fusionar esta PR publica los horarios nuevos. El flujo no fusiona nada.",
    ]
    return "\n".join(out) + "\n"
