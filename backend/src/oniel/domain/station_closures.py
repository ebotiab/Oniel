"""Trayectos en los que el visor simula el cierre entre estaciones de viajeros."""

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
_JOURNEYS = (
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
