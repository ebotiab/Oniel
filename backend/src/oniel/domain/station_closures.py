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


_JOURNEYS = (
    *_access_closures(),
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
