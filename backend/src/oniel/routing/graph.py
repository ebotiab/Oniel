"""Grafo de todas las líneas cargadas y recorridos entre dos nodos.

Los nodos del grafo son los de la red (un nodo común a dos líneas es uno solo) y las aristas son
los tramos. Sobre el grafo se aplica un escenario (``oniel.routing.scenario``) y se piden:

* ``find_routes``: los recorridos distintos entre dos nodos, del más corto al más largo.
* ``closure_detours``: los rodeos que salvan un tramo cerrado saliendo de su línea.
* ``route_along``: lo que cuesta un camino ya conocido, tramo a tramo.

Cada recorrido lleva kilómetros, tiempo estimado, kilómetros de vía única, líneas usadas y
estaciones principales intermedias. El método está en ``docs/simulacion.md``, «Grafo y
escenarios», y ``frontend/src/routing/graph.ts`` hace el mismo cálculo en el cliente: los dos
tienen que dar lo mismo (``backend/tests/test_routing.py`` y ``frontend/e2e/rutas.spec.ts``).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field, replace
from typing import Protocol

from pydantic import BaseModel

from oniel.routing.scenario import Scenario, ScenarioError

#: Veces que un recorrido pasa de una línea a otra si no se pide otra cosa. Es un freno técnico
#: (hasta seis líneas encadenadas), no un criterio: lo que descarta recorridos es ``max_ratio``.
DEFAULT_MAX_CHANGES = 5
#: Un recorrido se descarta si, donde se aparta de otro más corto, su rodeo mide más de estas
#: veces lo que el otro recorre entre los mismos dos puntos (``_strays``).
DEFAULT_MAX_RATIO = 2.0
#: Tope de recorridos devueltos, para que una red más grande no dispare la lista.
MAX_ROUTES = 12
#: Holgura al comparar kilómetros de una línea, como en el resto de Oniel.
KM_TOLERANCE = 0.05
#: Nombre de un enlace esbozado cuando hace de «línea» en un recorrido.
SKETCH_NAME = "Enlace esbozado"


@dataclass(frozen=True)
class GraphNode:
    id: str
    name: str
    kind: str
    rank: str


@dataclass(frozen=True)
class Edge:
    """Un tramo (o un enlace esbozado, con ``line_id`` nulo) entre dos nodos."""

    id: str
    line_id: str | None
    a: str
    b: str
    length_km: float
    #: Velocidad habitual; la máxima si no hay habitual; nula si no se conoce ninguna.
    speed_kmh: float | None
    tracks: int | None

    def other(self, node_id: str) -> str:
        return self.b if node_id == self.a else self.a


@dataclass(frozen=True)
class Graph:
    nodes: dict[str, GraphNode]
    edges: tuple[Edge, ...]
    line_names: dict[str, str]
    #: Kilómetro de cada nodo en cada línea a la que pertenece.
    line_km: dict[str, dict[str, float]]
    #: Los baipases: el id de cada línea que lo es y el de la línea de la que lo es. Un baipás
    #: cuenta como parte de su línea: pasar a él o volver de él no es cambiar de línea, y dos
    #: caminos que solo se distinguen por ir por él o por lo que rodea son el mismo recorrido.
    bypass_of: dict[str, str] = field(default_factory=dict)
    #: Los enlaces: el id de cada línea que lo es y el de la línea de la que cuelga. Un enlace
    #: también cuenta como parte de su línea, pero no une dos nodos de ella: va de uno de sus nodos
    #: a un nodo de otra línea, y con las dos forma un triángulo (``link_sides``).
    link_of: dict[str, str] = field(default_factory=dict)
    _adjacent: dict[str, list[Edge]] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        for edge in self.edges:
            self._adjacent.setdefault(edge.a, []).append(edge)
            self._adjacent.setdefault(edge.b, []).append(edge)

    def edges_at(self, node_id: str) -> list[Edge]:
        return self._adjacent.get(node_id, [])

    def edge(self, edge_id: str) -> Edge | None:
        return next((e for e in self.edges if e.id == edge_id), None)

    def line_key(self, edge: Edge) -> str:
        """La línea por la que cuenta un tramo: la suya o, si es de un baipás o de un enlace, la
        línea de la que cuelga.

        Un enlace esbozado cuenta como una línea propia.
        """
        if edge.line_id is None:
            return edge.id
        return self.bypass_of.get(edge.line_id) or self.link_of.get(edge.line_id, edge.line_id)

    def link_sides(self) -> dict[str, tuple[str, int]]:
        """De cada tramo que es lado del triángulo de un enlace, de qué enlace y qué lado.

        Un enlace cierra un triángulo con las dos líneas que une: sus lados son el enlace y el
        trecho de cada línea desde un extremo del enlace hasta el nodo en el que las dos se
        juntan. El de Monforte del Cid va de la línea de Alicante a la de Murcia, que se separan
        en la bifurcación de Murcia: los lados son el enlace, el tramo de Monforte del Cid a la
        bifurcación de Murcia y el de esta a la bifurcación Vinalopó. Las vías de un triángulo así
        no dejan doblar sus esquinas: de un lado a otro solo se pasa invirtiendo la marcha, y un
        recorrido no lo hace (``_walk``).
        """
        sides: dict[str, tuple[str, int]] = {}
        for line_id, parent in self.link_of.items():
            own = self.line_km.get(line_id, {})
            on_parent = self.line_km.get(parent)
            if len(own) < 2 or on_parent is None:
                continue
            ends = (min(own, key=lambda n: own[n]), max(own, key=lambda n: own[n]))
            joins = [n for n in ends if n in on_parent]
            away = [n for n in ends if n not in on_parent]
            if len(joins) != 1 or len(away) != 1:
                continue
            join, far = joins[0], away[0]
            best: tuple[float, str, str] | None = None
            for other, km in sorted(self.line_km.items()):
                if other in (line_id, parent) or far not in km:
                    continue
                if other in self.bypass_of or other in self.link_of:
                    continue
                for apex in sorted(km):
                    if apex in on_parent and apex not in (far, join):
                        around = abs(km[apex] - km[far]) + abs(on_parent[apex] - on_parent[join])
                        if best is None or around < best[0]:
                            best = (around, other, apex)
            if best is None:
                continue
            _, other, apex = best
            for edge in self.edges:
                if edge.line_id == line_id:
                    sides[edge.id] = (line_id, 0)
            for index, (side, a, b) in enumerate(((other, far, apex), (parent, apex, join)), 1):
                km = self.line_km[side]
                lo, hi = sorted((km[a], km[b]))
                for edge in self.edges:
                    if edge.line_id != side or edge.a not in km or edge.b not in km:
                        continue
                    near, beyond = sorted((km[edge.a], km[edge.b]))
                    if lo - KM_TOLERANCE <= near and beyond <= hi + KM_TOLERANCE:
                        sides[edge.id] = (line_id, index)
        return sides

    def bypass_spans(self) -> list[tuple[str, str, str]]:
        """Por cada baipás, la línea de la que lo es y los dos nodos de esta que une."""
        spans = []
        for line_id, parent in self.bypass_of.items():
            km = self.line_km.get(line_id, {})
            if len(km) < 2 or parent not in self.line_km:
                continue
            first, last = min(km, key=lambda n: km[n]), max(km, key=lambda n: km[n])
            if first in self.line_km[parent] and last in self.line_km[parent]:
                a, b = sorted((first, last))
                spans.append((parent, a, b))
        return spans

    def apply(self, scenario: Scenario) -> Graph:
        """El grafo con las modificaciones del escenario: cierres, velocidades y enlaces."""
        known = {e.id for e in self.edges}
        for segment_id in [*scenario.closures, *(v.segment_id for v in scenario.speeds)]:
            if segment_id not in known:
                raise ScenarioError(f"No hay ningún tramo con id {segment_id}")
        closed = set(scenario.closures)
        speed = {v.segment_id: v.speed_kmh for v in scenario.speeds}
        edges = [
            replace(e, speed_kmh=speed[e.id]) if e.id in speed else e
            for e in self.edges
            if e.id not in closed
        ]
        for link in scenario.links:
            for node_id in (link.from_node_id, link.to_node_id):
                if node_id not in self.nodes:
                    raise ScenarioError(f"No hay ningún nodo con id {node_id}")
            if link.from_node_id == link.to_node_id:
                raise ScenarioError("Un enlace tiene que unir dos nodos distintos")
            edges.append(
                Edge(
                    id=link.id,
                    line_id=None,
                    a=link.from_node_id,
                    b=link.to_node_id,
                    length_km=link.length_km,
                    speed_kmh=link.speed_kmh,
                    tracks=None,
                )
            )
        return Graph(
            self.nodes, tuple(edges), self.line_names, self.line_km, self.bypass_of, self.link_of
        )


class LineLike(Protocol):
    """Lo que el grafo necesita de una línea (``LineSummary`` lo cumple)."""

    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def bypass_of(self) -> str | None: ...
    @property
    def link_of(self) -> str | None: ...


class NodeLike(Protocol):
    """Un nodo en una línea, con su kilómetro en ella (``NodeOut``)."""

    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def kind(self) -> str: ...
    @property
    def rank(self) -> str: ...
    @property
    def line_id(self) -> str: ...
    @property
    def km(self) -> float: ...


class SegmentLike(Protocol):
    """Un tramo entre dos nodos (``SegmentOut``)."""

    @property
    def id(self) -> str: ...
    @property
    def line_id(self) -> str: ...
    @property
    def from_node_id(self) -> str: ...
    @property
    def to_node_id(self) -> str: ...
    @property
    def length_km(self) -> float: ...
    @property
    def max_speed_kmh(self) -> int | None: ...
    @property
    def typical_speed_kmh(self) -> int | None: ...
    @property
    def tracks(self) -> int | None: ...
    @property
    def status(self) -> str: ...


def build_graph(
    lines: Iterable[LineLike], nodes: Iterable[NodeLike], segments: Iterable[SegmentLike]
) -> Graph:
    """Grafo de la red disponible. ``nodes`` trae cada nodo una vez por línea, con su km en ella."""
    graph_nodes: dict[str, GraphNode] = {}
    line_km: dict[str, dict[str, float]] = {}
    for n in nodes:
        graph_nodes.setdefault(n.id, GraphNode(n.id, n.name, n.kind, n.rank))
        line_km.setdefault(n.line_id, {})[n.id] = n.km
    edges = tuple(
        Edge(
            id=s.id,
            line_id=s.line_id,
            a=s.from_node_id,
            b=s.to_node_id,
            length_km=s.length_km,
            speed_kmh=s.typical_speed_kmh or s.max_speed_kmh,
            tracks=s.tracks,
        )
        for s in segments
        if s.status == "disponible"
    )
    lines = list(lines)
    return Graph(
        graph_nodes,
        edges,
        {line.id: line.name for line in lines},
        line_km,
        {line.id: line.bypass_of for line in lines if line.bypass_of is not None},
        {line.id: line.link_of for line in lines if line.link_of is not None},
    )


class RouteLeg(BaseModel):
    """Trecho de un recorrido por una sola línea (o por un enlace esbozado, sin ``line_id``)."""

    line_id: str | None
    line_name: str
    from_node_id: str
    from_name: str
    to_node_id: str
    to_name: str
    length_km: float
    time_min: int | None
    single_track_km: float


class Route(BaseModel):
    """Un recorrido entre dos nodos, con lo que cuesta."""

    from_node_id: str
    from_name: str
    to_node_id: str
    to_name: str
    length_km: float
    #: Minutos a la velocidad habitual de cada tramo, sin paradas; nulo si falta alguna velocidad.
    time_min: int | None
    single_track_km: float
    line_ids: list[str]
    legs: list[RouteLeg]
    #: Estaciones principales intermedias, en el orden en que se recorren.
    via: list[str]
    node_ids: list[str]
    segment_ids: list[str]


class Detour(BaseModel):
    """Rodeo que salva un tramo cerrado: sale de su línea en un nodo y vuelve a ella en otro."""

    route: Route
    #: Kilómetros entre esos dos nodos por la línea del tramo cerrado.
    closed_line_length_km: float


class ClosureDetours(BaseModel):
    """Los rodeos que salvan un tramo cerrado y cuántos más largos se han dejado fuera."""

    detours: list[Detour]
    #: Rodeos que existen y no se listan, por desproporcionados o por pasar del tope.
    omitted: int


#: Un paso del camino: la arista y el nodo al que llega.
_Step = tuple[Edge, str]


def _walk(
    graph: Graph,
    start: str,
    is_goal: Callable[[str], bool],
    may_pass: Callable[[str], bool],
    edge_ok: Callable[[Edge], bool],
    max_changes: int | None,
) -> Iterator[list[_Step]]:
    """Caminos simples desde ``start`` hasta un nodo meta, en profundidad.

    Un camino termina al llegar a una meta; solo atraviesa los nodos que ``may_pass`` admite y no
    cambia de línea más de ``max_changes`` veces. Cada enlace esbozado cuenta como una línea, y un
    baipás o un enlace cargado, como parte de la suya. Tampoco pasa de un lado a otro del
    triángulo de un enlace (``Graph.link_sides``): sería invertir la marcha.
    """
    path: list[_Step] = []
    visited = {start}
    sides = graph.link_sides()

    def visit(node_id: str, changes: int) -> Iterator[list[_Step]]:
        for edge in graph.edges_at(node_id):
            nxt = edge.other(node_id)
            if nxt in visited or not edge_ok(edge):
                continue
            previous = path[-1][0] if path else None
            if previous is not None and previous.id in sides and edge.id in sides:
                (link, side), (other_link, other_side) = sides[previous.id], sides[edge.id]
                if link == other_link and side != other_side:
                    continue
            changed = previous is not None and graph.line_key(previous) != graph.line_key(edge)
            total = changes + (1 if changed else 0)
            if max_changes is not None and total > max_changes:
                continue
            path.append((edge, nxt))
            if is_goal(nxt):
                yield list(path)
            elif may_pass(nxt):
                visited.add(nxt)
                yield from visit(nxt, total)
                visited.discard(nxt)
            path.pop()

    yield from visit(start, 0)


def _round1(value: float) -> float:
    """Redondeo a una décima, con la misma fórmula que el cliente."""
    return math.floor(value * 10 + 0.5) / 10


def _raw_length(steps: list[_Step]) -> float:
    total = 0.0
    for edge, _ in steps:
        total += edge.length_km
    return total


def _time_min(edges: list[Edge]) -> int | None:
    hours = 0.0
    for edge in edges:
        if not edge.speed_kmh:
            return None
        hours += edge.length_km / edge.speed_kmh
    return math.floor(hours * 60 + 0.5)


def _single_track(edges: list[Edge]) -> float:
    total = 0.0
    for edge in edges:
        if edge.tracks == 1:
            total += edge.length_km
    return total


def _route(graph: Graph, start: str, steps: list[_Step]) -> Route:
    # Trechos: aristas seguidas de la misma línea, con sus baipases dentro.
    groups: list[tuple[str, list[_Step]]] = []
    at = start
    for step in steps:
        if groups and graph.line_key(groups[-1][1][-1][0]) == graph.line_key(step[0]):
            groups[-1][1].append(step)
        else:
            groups.append((at, [step]))
        at = step[1]
    legs: list[RouteLeg] = []
    length = 0.0
    for leg_start, leg_steps in groups:
        edges = [e for e, _ in leg_steps]
        leg_end = leg_steps[-1][1]
        own = edges[0].line_id
        # El trecho es de la línea; si todo él va por un baipás, del baipás.
        line_id = own if all(e.line_id == own for e in edges) else graph.line_key(edges[0])
        # Por una línea, la distancia es la diferencia de sus kilómetros (lo que vaya por un
        # baipás suyo, la de los kilómetros del baipás); un enlace trae la suya.
        if own is not None:
            leg_length = 0.0
            run_line, run_start, at = own, leg_start, leg_start
            for edge, nxt in leg_steps:
                if edge.line_id is not None and edge.line_id != run_line:
                    km = graph.line_km[run_line]
                    leg_length += abs(km[at] - km[run_start])
                    run_line, run_start = edge.line_id, at
                at = nxt
            km = graph.line_km[run_line]
            leg_length += abs(km[at] - km[run_start])
        else:
            leg_length = edges[0].length_km
        length += leg_length
        legs.append(
            RouteLeg(
                line_id=line_id,
                line_name=graph.line_names[line_id] if line_id is not None else SKETCH_NAME,
                from_node_id=leg_start,
                from_name=graph.nodes[leg_start].name,
                to_node_id=leg_end,
                to_name=graph.nodes[leg_end].name,
                length_km=_round1(leg_length),
                time_min=_time_min(edges),
                single_track_km=_round1(_single_track(edges)),
            )
        )
    all_edges = [e for e, _ in steps]
    end = steps[-1][1]
    inner = [graph.nodes[n] for _, n in steps[:-1]]
    return Route(
        from_node_id=start,
        from_name=graph.nodes[start].name,
        to_node_id=end,
        to_name=graph.nodes[end].name,
        length_km=_round1(length),
        time_min=_time_min(all_edges),
        single_track_km=_round1(_single_track(all_edges)),
        line_ids=list(dict.fromkeys(leg.line_id for leg in legs if leg.line_id is not None)),
        legs=legs,
        via=[n.name for n in inner if n.kind == "estacion" and n.rank == "principal"],
        node_ids=[start, *(n for _, n in steps)],
        segment_ids=[e.id for e in all_edges],
    )


def route_along(graph: Graph, start: str, segment_ids: Iterable[str]) -> Route:
    """El recorrido que sale de ``start`` y sigue esos tramos en ese orden, con lo que cuesta.

    Sirve para medir un camino ya conocido (el de un tren, por ejemplo) con la misma vara que
    los que encuentra ``find_routes``.
    """
    if start not in graph.nodes:
        raise ScenarioError(f"No hay ningún nodo con id {start}")
    steps: list[_Step] = []
    at = start
    for segment_id in segment_ids:
        edge = graph.edge(segment_id)
        if edge is None:
            raise ScenarioError(f"No hay ningún tramo con id {segment_id}")
        if at not in (edge.a, edge.b):
            raise ScenarioError(f"El tramo {segment_id} no sale de {at}")
        at = edge.other(at)
        steps.append((edge, at))
    if not steps:
        raise ScenarioError("Un recorrido necesita al menos un tramo")
    return _route(graph, start, steps)


def _sorted(found: list[tuple[str, list[_Step]]]) -> list[tuple[str, list[_Step]]]:
    """Del más corto al más largo; a igual longitud, por los tramos que recorre."""
    return sorted(found, key=lambda f: (_raw_length(f[1]), [e.id for e, _ in f[1]]))


def _bypass_key(graph: Graph, start: str, steps: list[_Step]) -> tuple[str, ...]:
    """Lo que tienen en común los caminos que solo se distinguen por ir por un baipás o por lo que rodea.

    Es la lista de sus tramos, con una misma marca en lugar de los tramos del baipás o de los de
    su línea entre los dos nodos que el baipás une, cuando el camino los recorre de punta a punta.
    """
    spans = graph.bypass_spans()
    if not spans:
        return tuple(e.id for e, _ in steps)
    nodes = [start, *(n for _, n in steps)]
    edges = [e for e, _ in steps]
    key: list[str] = []
    i = 0
    while i < len(edges):
        whole = None
        for parent, a, b in spans:
            if nodes[i] not in (a, b) or graph.line_key(edges[i]) != parent:
                continue
            # hasta el otro nodo sin salir de la línea ni cambiar entre ella y el baipás
            far = b if nodes[i] == a else a
            j = i
            while j < len(edges) and edges[j].line_id == edges[i].line_id and nodes[j + 1] != far:
                j += 1
            if j < len(edges) and edges[j].line_id == edges[i].line_id:
                whole = (f"~{parent}:{a}:{b}", j + 1)
                break
        if whole is None:
            key.append(edges[i].id)
            i += 1
        else:
            key.append(whole[0])
            i = whole[1]
    return tuple(key)


def _without_bypass_twins(
    graph: Graph, ordered: list[tuple[str, list[_Step]]]
) -> list[tuple[str, list[_Step]]]:
    """De los caminos que solo cambian un baipás por lo que rodea, el primero (el más corto)."""
    seen: set[tuple[str, ...]] = set()
    kept = []
    for start, steps in ordered:
        key = (start, *_bypass_key(graph, start, steps))
        if key not in seen:
            seen.add(key)
            kept.append((start, steps))
    return kept


def _strays(steps: list[_Step], shorter: list[_Step], max_ratio: float) -> bool:
    """Si un camino se aparta de otro más corto y da un rodeo desproporcionado hasta reencontrarlo.

    Se quitan los tramos que los dos comparten al principio y al final y se compara lo que queda
    de cada uno: el camino se descarta si su parte propia mide más de ``max_ratio`` veces la del
    corto. Sin tramos comunes es la comparación de las dos longitudes enteras. Vale igual en los
    dos sentidos, así que invertir origen y destino da los mismos recorridos.
    """
    a, b = [e for e, _ in steps], [e for e, _ in shorter]
    shared = min(len(a), len(b))
    head = 0
    while head < shared and a[head].id == b[head].id:
        head += 1
    tail = 0
    while tail < shared - head and a[len(a) - 1 - tail].id == b[len(b) - 1 - tail].id:
        tail += 1
    own = 0.0
    for edge in a[head : len(a) - tail]:
        own += edge.length_km
    other = 0.0
    for edge in b[head : len(b) - tail]:
        other += edge.length_km
    return own > other * max_ratio


def find_routes(
    graph: Graph,
    from_node_id: str,
    to_node_id: str,
    scenario: Scenario | None = None,
    *,
    max_changes: int | None = DEFAULT_MAX_CHANGES,
    max_ratio: float | None = DEFAULT_MAX_RATIO,
) -> list[Route]:
    """Recorridos distintos entre dos nodos con la red del escenario, del más corto al más largo.

    Son los caminos que no pasan dos veces por el mismo nodo, cambian de línea como mucho
    ``max_changes`` veces (``None``, sin tope) y no dan un rodeo de más de ``max_ratio`` veces
    respecto a otro más corto, medido donde se apartan de él (``_strays``; ``None``, sin descartar
    ninguno por largo). Un baipás es parte de su línea: de los caminos que solo se distinguen por
    ir por él o por la estación que rodea queda el más corto, y cuenta como un recorrido. Un
    enlace también es parte de su línea, y ningún camino dobla una esquina de su triángulo.
    """
    for node_id in (from_node_id, to_node_id):
        if node_id not in graph.nodes:
            raise ScenarioError(f"No hay ningún nodo con id {node_id}")
    if from_node_id == to_node_id:
        return []
    g = graph.apply(scenario) if scenario is not None else graph
    found = [
        (from_node_id, steps)
        for steps in _walk(
            g, from_node_id, lambda n: n == to_node_id, lambda n: True, lambda e: True, max_changes
        )
    ]
    ordered = _without_bypass_twins(g, _sorted(found))
    if max_ratio is not None:
        kept: list[tuple[str, list[_Step]]] = []
        for candidate in ordered:
            if not any(_strays(candidate[1], shorter[1], max_ratio) for shorter in kept):
                kept.append(candidate)
        ordered = kept
    return [_route(g, start, steps) for start, steps in ordered[:MAX_ROUTES]]


def _along(graph: Graph, line_id: str, a: str, b: str) -> list[_Step]:
    """Los tramos de la línea entre dos de sus nodos, en el sentido en que crecen sus kilómetros."""
    km = graph.line_km[line_id]
    lo, hi = km[a] - KM_TOLERANCE, km[b] + KM_TOLERANCE
    steps: list[tuple[float, _Step]] = []
    for edge in graph.edges:
        if edge.line_id != line_id or edge.a not in km or edge.b not in km:
            continue
        near, far = sorted((edge.a, edge.b), key=lambda n: km[n])
        if km[near] >= lo and km[far] <= hi:
            steps.append((km[near], (edge, far)))
    return [step for _, step in sorted(steps, key=lambda s: s[0])]


def closure_detours(
    graph: Graph,
    segment_id: str,
    scenario: Scenario | None = None,
    *,
    max_ratio: float | None = DEFAULT_MAX_RATIO,
) -> ClosureDetours:
    """Rodeos que salvan el tramo ``segment_id`` cerrado, del más corto al más largo.

    Un rodeo sale de la línea del tramo en un nodo situado antes del cierre, no vuelve a tocarla
    hasta un nodo situado después y no usa ninguno de sus tramos. Al no pasar por nodos
    intermedios de la línea, cada rodeo es el más ceñido al tramo de los que siguen su camino.
    El resto del escenario (otros cierres, enlaces, velocidades) se aplica también.

    Como en ``find_routes``, se descarta el rodeo desproporcionado respecto a otro más corto
    (``max_ratio``; ``None``, sin descartar ninguno). Dos rodeos pueden salir de la línea y
    volver a ella en nodos distintos, así que para compararlos se completa cada uno con los
    tramos de la propia línea hasta cubrir el mismo trecho, del nodo de salida más temprano al
    de vuelta más tardío, y se les aplica la misma regla (``_strays``). El más corto se conserva
    siempre, mida lo que mida: que exista otro camino es parte de la respuesta. ``omitted`` cuenta
    los que se dejan fuera, para que quien consulta sepa que los hay.
    """
    closed = graph.edge(segment_id)
    if closed is None or closed.line_id is None:
        raise ScenarioError(f"No hay ningún tramo con id {segment_id}")
    line_id = closed.line_id
    km = graph.line_km[line_id]
    lo, hi = sorted((km[closed.a], km[closed.b]))
    g = graph.apply((scenario or Scenario()).with_closures([segment_id]))
    # Los nodos anteriores, del más cercano al tramo al más lejano.
    before = sorted((n for n in km if km[n] <= lo + KM_TOLERANCE), key=lambda n: -km[n])
    after = {n for n in km if km[n] >= hi - KM_TOLERANCE}
    found = [
        (start, steps)
        for start in before
        for steps in _walk(
            g,
            start,
            lambda n: n in after,
            lambda n: n not in km,
            lambda e: e.line_id != line_id,
            None,
        )
    ]
    found = _without_bypass_twins(g, _sorted(found))
    ordered = found
    if max_ratio is not None:

        def whole(start: str, steps: list[_Step], first: str, last: str) -> list[_Step]:
            end = steps[-1][1]
            return [
                *_along(graph, line_id, first, start),
                *steps,
                *_along(graph, line_id, end, last),
            ]

        kept: list[tuple[str, list[_Step]]] = []
        for start, steps in ordered:
            end = steps[-1][1]
            strays = False
            for other_start, other_steps in kept:
                first = min(start, other_start, key=lambda n: km[n])
                last = max(end, other_steps[-1][1], key=lambda n: km[n])
                if _strays(
                    whole(start, steps, first, last),
                    whole(other_start, other_steps, first, last),
                    max_ratio,
                ):
                    strays = True
                    break
            if not strays:
                kept.append((start, steps))
        ordered = kept
    listed = ordered[:MAX_ROUTES]
    return ClosureDetours(
        detours=[
            Detour(
                route=_route(g, start, steps),
                closed_line_length_km=_round1(km[steps[-1][1]] - km[start]),
            )
            for start, steps in listed
        ],
        omitted=len(found) - len(listed),
    )
