"""Trayectos en los que el visor simula el cierre entre estaciones de viajeros."""

from itertools import pairwise

from pydantic import BaseModel


class StationClosure(BaseModel):
    from_id: str
    to_id: str
    from_name: str
    to_name: str
    segment_ids: tuple[str, ...]


_LINE = "alcazar-albacete"
_COAST = "valencia-xativa-alicante"
_LINK = "enlace-la-encina-caudete"
_ACCESS = "enlace-principe-pio-pinar"
_ACCESS_STATIONS = (
    ("madrid-principe-pio", "Madrid-Príncipe Pío"),
    ("aravaca", "Aravaca"),
    ("pozuelo", "Pozuelo"),
    ("el-barrial-centro-comercial-pozuelo", "El Barrial-Centro Comercial Pozuelo"),
    ("majadahonda", "Majadahonda"),
    ("las-rozas", "Las Rozas"),
    ("pinar-de-las-rozas", "Pinar de las Rozas"),
)


def _access_closures() -> tuple[StationClosure, ...]:
    journeys = []
    for (start, start_name), (end, end_name) in pairwise(_ACCESS_STATIONS):
        nodes = (
            (start, "bif-chamartin", "aguja-bif-chamartin", end)
            if start == "las-rozas"
            else (start, end)
        )
        journeys.append(
            StationClosure(
                from_id=start,
                from_name=start_name,
                to_id=end,
                to_name=end_name,
                segment_ids=tuple(f"{_ACCESS}:{a}:{b}" for a, b in pairwise(nodes)),
            )
        )
    return tuple(journeys)


def _salamanca_closures() -> tuple[StationClosure, ...]:
    """Cada franja del esquema lleva al trayecto entre dos estaciones con horario."""
    line = "avila-salamanca"
    main = "madrid-avila-valladolid"
    junction = "bif-avila-salamanca"
    shared = f"{main}:avila:{junction}"
    stations = (
        ("avila", "Ávila"),
        ("cardenosa-de-avila", "Cardeñosa de Ávila"),
        ("san-pedro-del-arroyo", "San Pedro del Arroyo"),
        ("crespos", "Crespos"),
        ("narros-del-castillo", "Narros del Castillo"),
        ("penaranda-de-bracamonte", "Peñaranda de Bracamonte"),
        ("villar-de-gallimazo", "Villar de Gallimazo"),
        ("babilafuente", "Babilafuente"),
        ("san-morales", "San Morales"),
        ("aldealengua", "Aldealengua"),
        ("salamanca", "Salamanca"),
        ("salamanca-la-alamedilla", "Salamanca-La Alamedilla"),
    )
    journeys = [
        StationClosure(
            from_id="avila",
            from_name="Ávila",
            to_id="arevalo",
            to_name="Arévalo",
            segment_ids=(shared, f"{main}:{junction}:arevalo"),
        ),
    ]
    for (start, start_name), (end, end_name) in pairwise(stations):
        nodes: tuple[str, ...] = (start, end)
        if start == "avila":
            nodes = (junction, "salida-avila-penaranda", end)
        elif end == "salamanca":
            nodes = (
                start,
                "entrada-salamanca-por-avila",
                "desvio-acceso-salamanca",
                "bif-acceso-salamanca",
                end,
            )
        segments = tuple(f"{line}:{a}:{b}" for a, b in pairwise(nodes))
        journeys.append(
            StationClosure(
                from_id=start,
                from_name=start_name,
                to_id=end,
                to_name=end_name,
                segment_ids=(shared, *segments) if start == "avila" else segments,
            )
        )
    return tuple(journeys)


def _medina_closures() -> tuple[StationClosure, ...]:
    line = "medina-del-campo-salamanca"
    link = "enlace-medina-av-salamanca"
    lav = "lav-olmedo-ourense"
    medina = "medina-del-campo"
    av = "medina-del-campo-av"
    branch = "bif-medina-av-salamanca"
    changer = "cambiador-medina-av"
    junction = "bif-arroyo-de-la-golosa"
    entry = "bif-acceso-salamanca"
    stations = (
        (medina, "Medina del Campo"),
        ("campillo", "Campillo"),
        ("el-carpio", "El Carpio"),
        ("fresno-el-viejo", "Fresno el Viejo"),
        ("cantalapiedra", "Cantalapiedra"),
        ("el-pedroso-de-la-armuna", "El Pedroso de la Armuña"),
        ("pitiegua", "Pitiegua"),
        ("gomecello", "Gomecello"),
        ("moriscos", "Moriscos"),
        ("salamanca", "Salamanca"),
    )
    common = f"{lav}:{av}:{branch}"
    journeys = [
        StationClosure(
            from_id=av,
            from_name="Medina del Campo Alta Velocidad",
            to_id="zamora",
            to_name="Zamora",
            segment_ids=(
                common,
                f"{lav}:{branch}:toro-av",
                f"{lav}:toro-av:coreses",
                f"{lav}:coreses:zamora",
            ),
        ),
        StationClosure(
            from_id=av,
            from_name="Medina del Campo Alta Velocidad",
            to_id="campillo",
            to_name="Campillo",
            segment_ids=(
                common,
                f"{link}:{branch}:{changer}",
                f"{link}:{changer}:{junction}",
                f"{line}:{junction}:campillo",
            ),
        ),
    ]
    for (start, name), (end, end_name) in pairwise(stations):
        nodes = (start, "cambio-tension-medina", junction, end) if start == medina else (start, end)
        segments = tuple(f"{line}:{a}:{b}" for a, b in pairwise(nodes))
        if end == "salamanca":
            segments = (f"{line}:{start}:{entry}", f"avila-salamanca:{entry}:{end}")
        journeys.append(
            StationClosure(
                from_id=start, from_name=name, to_id=end, to_name=end_name, segment_ids=segments
            )
        )
    return tuple(journeys)


_JOURNEYS = (
    *_medina_closures(),
    *_access_closures(),
    *_salamanca_closures(),
    StationClosure(
        from_id="albacete-los-llanos",
        to_id="almansa",
        from_name="Albacete-Los Llanos",
        to_name="Almansa",
        segment_ids=(
            f"{_LINE}:albacete-los-llanos:bif-chinchilla",
            f"{_LINE}:bif-chinchilla:almansa",
        ),
    ),
    StationClosure(
        from_id="almansa",
        to_id="la-encina",
        from_name="Almansa",
        to_name="La Encina",
        segment_ids=(f"{_LINE}:almansa:la-encina",),
    ),
    StationClosure(
        from_id="la-encina",
        to_id="xativa",
        from_name="La Encina",
        to_name="Xàtiva",
        segment_ids=(f"{_LINE}:la-encina:bif-la-encina", f"{_COAST}:xativa:bif-la-encina"),
    ),
    StationClosure(
        from_id="la-encina",
        to_id="caudete",
        from_name="La Encina",
        to_name="Caudete",
        segment_ids=(f"{_LINK}:la-encina:caudete",),
    ),
)

# El último tramo hasta Xàtiva participa en el cierre del trayecto entero. Su ficha anterior
# conserva las prestaciones de la línea València–Alicante.
STATION_CLOSURES = {
    segment_id: journey
    for journey in _JOURNEYS
    for segment_id in journey.segment_ids
    if not segment_id.startswith(f"{_COAST}:")
}
