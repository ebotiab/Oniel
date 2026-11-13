"""Trenes por tramo y si la red cargada les ofrece otro camino cuando el tramo se corta.

Para cada tramo se miran los trenes que lo recorren un día. De cada tren se toma su recorrido
por las líneas cargadas, del nodo por el que entra al nodo por el que sale, y se pregunta al
grafo de rutas (``oniel.routing``) por el camino más corto entre esos dos nodos con el tramo
cerrado. Si existe y no mide más del doble que el recorrido del tren, se dice cuántos kilómetros
y minutos le añade; si no, el tren no tiene alternativa. El tope es el mismo que el del
comparador y el de los rodeos de un cierre (``DEFAULT_MAX_RATIO``): dar la vuelta a media red
no es otro camino.

«Sin alternativa» significa siempre «en las líneas que Oniel tiene cargadas», no en la red
real. El cálculo no decide si el tren podría tomar ese camino (ancho de vía, paradas, capacidad
de la vía): solo dice que el camino existe y lo que mide. El método y sus límites están en
``docs/simulacion.md``, «Tramos sin alternativa».
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from oniel.domain.schemas import (
    AlternativeRouteOut,
    SegmentAlternativesOut,
    SegmentTrainGroupOut,
)
from oniel.routing import (
    DEFAULT_MAX_RATIO,
    Edge,
    Graph,
    Route,
    Scenario,
    find_routes,
    route_along,
)

#: Lo que el resultado dice siempre de su alcance.
SCOPE_NOTE = (
    "«Sin alternativa» quiere decir que no hay otro camino en las líneas que Oniel tiene"
    " cargadas, no que no exista en la red real. Un camino que mide más del doble que el"
    " recorrido del tren no cuenta como otro camino. Oniel solo comprueba que el camino existe y"
    " cuánto mide: no mira si el tren cabe por él (ancho de vía, paradas, sitio en la vía)."
)
#: Cómo se calcula, para quien lea el resultado sin la documentación delante.
METHOD = (
    "De cada tren que recorre el tramo un día se toma su recorrido por las líneas cargadas, del"
    " nodo por el que entra al nodo por el que sale. Con el tramo cerrado, Oniel busca en el grafo"
    " de todas las líneas cargadas el camino más corto entre esos dos nodos y lo compara con el"
    " recorrido del tren: kilómetros medidos por cada línea y minutos a la velocidad habitual de"
    " cada tramo, sin paradas. Si ese camino mide más del doble que el recorrido del tren, no"
    " cuenta. Los trenes con el mismo recorrido forman un grupo. No se aplican"
    " las interrupciones vigentes: cada tramo se cierra por separado sobre la red completa."
)


@dataclass(frozen=True)
class ServicePath:
    """Un tren de un día: su operador y los tramos cargados que recorre."""

    service_id: str
    operator_id: str
    segment_ids: frozenset[str]


def corridor(graph: Graph, segment_ids: Iterable[str], through: str) -> tuple[str, list[Edge]]:
    """El recorrido seguido de un tren que contiene el tramo ``through``: su origen y sus tramos.

    De los tramos del tren se toman los que están unidos al tramo pedido (un tren que sale de las
    líneas cargadas y vuelve a entrar tiene dos trozos sueltos). Si forman un camino sin
    bifurcaciones, ese es el recorrido, del extremo que va antes en la red al otro. Si no, el
    recorrido se queda en el propio tramo.
    """
    asked = graph.edge(through)
    if asked is None:
        raise ValueError(f"No hay ningún tramo con id {through}")
    own = {e.id: e for e in graph.edges if e.id in set(segment_ids)}
    own[asked.id] = asked
    # Los tramos unidos al pedido.
    joined: dict[str, Edge] = {asked.id: asked}
    frontier = [asked]
    while frontier:
        edge = frontier.pop()
        for other in own.values():
            if other.id not in joined and {other.a, other.b} & {edge.a, edge.b}:
                joined[other.id] = other
                frontier.append(other)
    degree: Counter[str] = Counter()
    for edge in joined.values():
        degree[edge.a] += 1
        degree[edge.b] += 1
    order = {node_id: i for i, node_id in enumerate(graph.nodes)}
    ends = sorted((n for n, d in degree.items() if d == 1), key=lambda n: order[n])
    if len(ends) != 2 or any(d > 2 for d in degree.values()):
        start = min((asked.a, asked.b), key=lambda n: order[n])
        return start, [asked]
    path: list[Edge] = []
    at = ends[0]
    left = dict(joined)
    while left:
        edge = next(e for e in left.values() if at in (e.a, e.b))
        del left[edge.id]
        path.append(edge)
        at = edge.other(at)
    return ends[0], path


def _alternative(own: Route, other: Route) -> AlternativeRouteOut:
    return AlternativeRouteOut(
        length_km=other.length_km,
        time_min=other.time_min,
        extra_km=round(other.length_km - own.length_km, 1),
        extra_min=(
            other.time_min - own.time_min
            if other.time_min is not None and own.time_min is not None
            else None
        ),
        single_track_km=other.single_track_km,
        line_ids=other.line_ids,
        via=other.via,
    )


def other_way(own: Route, others: Sequence[Route], max_ratio: float | None) -> Route | None:
    """El otro camino de un recorrido: el más corto de ``others``, si no pasa del tope.

    ``others`` va del más corto al más largo. Con ``max_ratio`` se descarta el que mide más de
    esas veces lo que mide el recorrido del tren: existe, pero no es un desvío que tomar.
    """
    if not others:
        return None
    shortest = others[0]
    if max_ratio is not None and shortest.length_km > max_ratio * own.length_km:
        return None
    return shortest


def segment_alternatives(
    graph: Graph, services: Sequence[ServicePath], max_ratio: float | None = DEFAULT_MAX_RATIO
) -> list[SegmentAlternativesOut]:
    """Por cada tramo del grafo, sus trenes y la alternativa de cada grupo de trenes.

    Los trenes de un tramo se agrupan por su recorrido en las líneas cargadas: todos los de un
    grupo entran y salen por los mismos nodos y siguen el mismo camino, así que comparten
    alternativa. Los grupos van del que más trenes tiene al que menos. Un camino que mide más de
    ``max_ratio`` veces el recorrido del tren no cuenta como alternativa; con ``None``, cuenta
    cualquiera.
    """
    out: list[SegmentAlternativesOut] = []
    for edge in graph.edges:
        if edge.line_id is None:
            continue
        # Trenes del tramo por recorrido: (origen, tramos en orden) → operadores, uno por tren.
        groups: dict[tuple[str, tuple[str, ...]], list[str]] = {}
        for service in services:
            if edge.id not in service.segment_ids:
                continue
            start, path = corridor(graph, service.segment_ids, edge.id)
            groups.setdefault((start, tuple(e.id for e in path)), []).append(service.operator_id)
        closed = Scenario(closures=[edge.id])
        group_outs: list[SegmentTrainGroupOut] = []
        for (start, path_ids), operators in groups.items():
            own = route_along(graph, start, path_ids)
            # Se buscan todos, sin el descarte del comparador (que compara caminos entre sí), y
            # el tope se aplica contra el recorrido del propio tren.
            others = find_routes(graph, own.from_node_id, own.to_node_id, closed, max_ratio=None)
            if not others:
                # Ni por número de líneas: un tren que cruza Madrid de una línea a otra (de
                # Valladolid a Valencia) puede necesitar más cambios de línea de los que admite
                # el comparador para rodear un tramo, y ese rodeo también es otro camino.
                others = find_routes(
                    graph,
                    own.from_node_id,
                    own.to_node_id,
                    closed,
                    max_changes=None,
                    max_ratio=None,
                )
            other = other_way(own, others, max_ratio)
            group_outs.append(
                SegmentTrainGroupOut(
                    from_node_id=own.from_node_id,
                    from_name=own.from_name,
                    to_node_id=own.to_node_id,
                    to_name=own.to_name,
                    trains=len(operators),
                    by_operator=dict(sorted(Counter(operators).items())),
                    length_km=own.length_km,
                    time_min=own.time_min,
                    line_ids=own.line_ids,
                    alternative=_alternative(own, other) if other is not None else None,
                )
            )
        group_outs.sort(key=lambda g: (-g.trains, g.from_name, g.to_name, g.length_km))
        by_operator: Counter[str] = Counter()
        for g in group_outs:
            by_operator.update(g.by_operator)
        with_alternative = sum(g.trains for g in group_outs if g.alternative is not None)
        trains = sum(g.trains for g in group_outs)
        out.append(
            SegmentAlternativesOut(
                segment_id=edge.id,
                trains=trains,
                by_operator=dict(sorted(by_operator.items())),
                with_alternative=with_alternative,
                without_alternative=trains - with_alternative,
                groups=group_outs,
            )
        )
    return out
