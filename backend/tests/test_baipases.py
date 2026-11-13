"""Los baipases de Zaragoza y de Lleida: dos líneas cortas que cuelgan de la alta velocidad de
Barcelona y llevan los trenes que no paran en la estación que rodean."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import (
    BCN_SPEC,
    BYPASS_LLEIDA_SPEC,
    BYPASS_ZARAGOZA_SPEC,
    DATA_DIR,
    FEED,
    OUIGO_FEED,
    OUIGO_STOP_ID_PREFIX,
    SOURCES,
    SPEC,
)
from pydantic import ValidationError

from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import LoadedLine, bypasses_of, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import (
    Bypass,
    BypassPiece,
    LineNode,
    LineSegment,
    SegmentPass,
    StopCall,
    resolve_passes,
)
from oniel.validate import expected_pk_km, loaded_line, validate_all

BCN = "lav-madrid-barcelona"

# Línea de juguete: de A a B, 200 km, con una estación S entre dos bifurcaciones, X e Y. Por la
# estación hay 25 km de X a Y; por el baipás, 20.
NODES = {
    "a": LineNode("a", 0.0, 0.0, 0.0, "A"),
    "x": LineNode("x", 100.0, 1.0, 0.0, "Bifurcación X"),
    "s": LineNode("s", 110.0, 1.1, 0.0, "S"),
    "y": LineNode("y", 125.0, 1.25, 0.0, "Bifurcación Y"),
    "b": LineNode("b", 200.0, 2.0, 0.0, "B"),
}
SEGMENTS = [
    LineSegment("a-x", 0.0, 100.0),
    LineSegment("x-s", 100.0, 110.0),
    LineSegment("s-y", 110.0, 125.0),
    LineSegment("y-b", 125.0, 200.0),
]
AROUND = Bypass(
    100.0, 125.0, (BypassPiece("baipas", 0.0, 20.0),), "No para en S: por eso va por aquí."
)


def hm(h: int, m: int) -> int:
    return h * 3600 + m * 60


def stop(seq: int, node: str, when: int) -> StopCall:
    return StopCall(seq, node, NODES[node].name, when, when, node_id=node)


def by_id(passes: list[SegmentPass]) -> dict[str, SegmentPass]:
    return {p.segment_id: p for p in passes}


def test_a_train_that_does_not_stop_between_the_two_junctions_takes_the_bypass() -> None:
    """A 8:00 → B 10:00 sin paradas: 100 km hasta X, 20 km por el baipás y 75 km desde Y, 195 km
    en 120 minutos. Llega a X a los 120 × 100 / 195 = 61,5 min (9:01:32) y a Y a los
    120 × 120 / 195 = 73,8 min (9:13:51). No pasa por los dos tramos de la estación."""
    calls = [stop(1, "a", hm(8, 0)), stop(2, "b", hm(10, 0))]
    passes, resolution = resolve_passes(calls, NODES, SEGMENTS, [AROUND])
    assert resolution == "completa"
    # los tramos de la línea, en su orden, y detrás el del baipás
    assert [p.segment_id for p in passes] == ["a-x", "y-b", "baipas"]
    p = by_id(passes)
    at_x = hm(8, 0) + 120 * 60 * 100 / 195
    at_y = hm(8, 0) + 120 * 60 * 120 / 195
    assert (p["a-x"].enter_s, p["a-x"].enter_margin_s) == (hm(8, 0), 0)
    assert p["a-x"].exit_s == pytest.approx(at_x) == p["baipas"].enter_s
    assert p["baipas"].exit_s == pytest.approx(at_y) == p["y-b"].enter_s
    assert (p["y-b"].exit_s, p["y-b"].exit_margin_s) == (hm(10, 0), 0)
    assert all(x.kind == "estimado" and x.km_increasing for x in p.values())
    # el margen es el de un tren con sus dos paradas en la línea: 15 % de las dos horas
    assert p["baipas"].enter_margin_s == p["baipas"].exit_margin_s == pytest.approx(18 * 60)
    # el paso por el baipás dice por qué el tren va por él; los demás, lo de siempre
    assert p["baipas"].basis.startswith("No para en S: por eso va por aquí. Estimado repartiendo")
    assert p["a-x"].basis.startswith("Estimado repartiendo los 02:00 h entre A (08:00) y B")

    # sin baipases declarados, el mismo tren recorre los cuatro tramos, 205 km
    plain = by_id(resolve_passes(calls, NODES, SEGMENTS)[0])
    assert set(plain) == {"a-x", "x-s", "s-y", "y-b"}
    assert plain["a-x"].exit_s == pytest.approx(hm(8, 0) + 120 * 60 * 100 / 200)


def test_a_train_that_stops_between_the_two_junctions_goes_through_the_station() -> None:
    calls = [stop(1, "a", hm(8, 0)), stop(2, "s", hm(9, 0)), stop(3, "b", hm(10, 0))]
    passes, _ = resolve_passes(calls, NODES, SEGMENTS, [AROUND])
    assert [p.segment_id for p in passes] == ["a-x", "x-s", "s-y", "y-b"]
    # tampoco lo toma el que sale de la línea por la estación hacia una parada de fuera
    leaving = [
        stop(1, "a", hm(8, 0)),
        StopCall(2, "fuera", "Fuera", hm(9, 30), hm(9, 30), 1.1, 0.5, exit_node_ids=("s",)),
    ]
    passes, _ = resolve_passes(leaving, NODES, SEGMENTS, [AROUND])
    assert [p.segment_id for p in passes] == ["a-x", "x-s"]
    # ni el que empieza en una de las dos bifurcaciones y acaba en la estación
    short = [stop(1, "x", hm(8, 0)), stop(2, "s", hm(8, 10))]
    assert [p.segment_id for p in resolve_passes(short, NODES, SEGMENTS, [AROUND])[0]] == ["x-s"]


def test_the_bypass_is_taken_in_both_directions_and_keeps_its_own_sense() -> None:
    """De B a A el tren recorre el baipás al revés. Si el kilometraje del baipás va en sentido
    contrario al de la línea, su paso lo dice con su propio sentido."""
    back = [stop(1, "b", hm(8, 0)), stop(2, "a", hm(10, 0))]
    p = by_id(resolve_passes(back, NODES, SEGMENTS, [AROUND])[0])
    assert set(p) == {"a-x", "y-b", "baipas"}
    assert all(x.km_increasing is False for x in p.values())
    assert p["y-b"].exit_s == pytest.approx(hm(8, 0) + 120 * 60 * 75 / 195) == p["baipas"].enter_s
    assert p["baipas"].exit_s == pytest.approx(hm(8, 0) + 120 * 60 * 95 / 195)

    reversed_bypass = Bypass(100.0, 125.0, (BypassPiece("baipas", 0.0, 20.0, False),))
    q = by_id(resolve_passes(back, NODES, SEGMENTS, [reversed_bypass])[0])
    assert q["baipas"].km_increasing is True and q["a-x"].km_increasing is False
    assert (q["baipas"].enter_s, q["baipas"].exit_s) == (p["baipas"].enter_s, p["baipas"].exit_s)
    assert q["baipas"].basis.startswith("Estimado repartiendo")  # sin frase, no la inventa


def test_two_bypasses_in_a_row_shorten_the_same_leg() -> None:
    """Con otro baipás de 30 km entre A y X (en vez de 100), el tren sin paradas recorre
    30 + 20 + 75 = 125 km, y los tiempos de los dos baipases encajan."""
    first = Bypass(
        0.0, 100.0, (BypassPiece("primero-1", 0.0, 10.0), BypassPiece("primero-2", 10.0, 30.0))
    )
    calls = [stop(1, "a", hm(8, 0)), stop(2, "b", hm(10, 0))]
    p = by_id(resolve_passes(calls, NODES, SEGMENTS, [first, AROUND])[0])
    assert set(p) == {"primero-1", "primero-2", "baipas", "y-b"}
    assert p["primero-1"].enter_s == hm(8, 0) and p["primero-1"].enter_margin_s == 0
    assert p["primero-2"].exit_s == pytest.approx(hm(8, 0) + 120 * 60 * 30 / 125)
    assert p["baipas"].enter_s == pytest.approx(p["primero-2"].exit_s)
    assert p["y-b"].enter_s == pytest.approx(hm(8, 0) + 120 * 60 * 50 / 125)


@pytest.fixture(scope="module")
def bcn() -> BuiltNetwork:
    return build_network(load_network_spec(BCN_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def zaragoza() -> BuiltNetwork:
    return build_network(load_network_spec(BYPASS_ZARAGOZA_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lleida() -> BuiltNetwork:
    return build_network(load_network_spec(BYPASS_LLEIDA_SPEC), DATA_DIR)


def test_each_bypass_is_one_segment_between_two_junctions_of_the_line(
    bcn: BuiltNetwork, zaragoza: BuiltNetwork, lleida: BuiltNetwork
) -> None:
    on_line = {n.spec.id: n for n in bcn.nodes}
    for net, ends, length, through in [
        (zaragoza, ["bif-moncasi", "bif-canal-imperial"], 20.7, 25.6),
        (lleida, ["bif-les-torres-de-sanui", "bif-artesa-de-lleida"], 14.3, 16.2),
    ]:
        assert net.spec.line.bypass_of == BCN
        assert [n.spec.id for n in net.nodes] == ends and len(net.segments) == 1
        # los dos extremos son nodos de la línea, que los define: aquí van como compartidos y
        # en el mismo punto
        assert all(n.spec.shared and n.offset_m < 1 for n in net.nodes)
        for n in net.nodes:
            theirs = on_line[n.spec.id]
            assert (n.lon, n.lat) == pytest.approx((theirs.lon, theirs.lat), abs=1e-4)
        assert net.line.polyline.length_km == pytest.approx(length, abs=0.05)
        a, b = (on_line[e].km for e in ends)
        assert b - a == pytest.approx(through, abs=0.05)
        segment = net.segments[0]
        assert (segment.max_speed_kmh, segment.typical_speed_kmh, segment.tracks) == (300, 300, 2)
        values = {k: segment.attributes[k].value for k in ("proteccion_tren", "bloqueo", "mando")}
        assert values == {
            "proteccion_tren": "ertms_n1_asfa",
            "bloqueo": "bca",
            "mando": "sin_dato_publicado",
        }
        assert not net.line.gaps_km and not net.line.joins_km
    # el de Zaragoza ahorra 4,9 km y el de Lleida, 2,0


def test_the_bypasses_carry_the_reference_pk_of_the_main_line(
    zaragoza: BuiltNetwork, lleida: BuiltNetwork
) -> None:
    """Los PK de Adif siguen por los baipases: cada uno arranca en el PK de su primera bifurcación
    y llega a la segunda con el suyo, a menos de 300 m de lo medido."""
    for net, first, last in [(zaragoza, 294.897, 315.783), (lleida, 434.565, 448.979)]:
        assert net.spec.line.pk_origin_km == first
        assert [n.spec.reference_pk_km for n in net.nodes] == [first, last]
        for n in net.nodes:
            assert expected_pk_km(net, n.km) == pytest.approx(n.spec.reference_pk_km, abs=0.3)


def test_sources_of_the_bypasses_are_registered() -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for path in (BYPASS_ZARAGOZA_SPEC, BYPASS_LLEIDA_SPEC):
        spec = load_network_spec(path)
        geometry = sources[spec.line.geometry_source.source_id]
        assert geometry.id == "osm-relation-11082425" and "los dos baipases" in str(
            geometry.coverage
        )
        assert spec.line.verification_source_id == "wikipedia-lav-madrid-barcelona"
        assert all(s.source_id in sources and s.checked_on for s in spec.attribute_sections)
        # los mismos operadores que la línea de la que sale, Iryo entre ellos
        main = load_network_spec(BCN_SPEC)
        assert spec.operators == main.operators and spec.line.zone == main.line.zone


def test_a_bypass_has_no_filter_of_its_own(feed: GtfsFeed) -> None:
    spec = load_network_spec(BYPASS_ZARAGOZA_SPEC)
    assert not spec.stop_mappings and not spec.route_overrides
    assert select_trips_for_spec(feed, spec) == []
    raw = json.loads(BYPASS_ZARAGOZA_SPEC.read_text(encoding="utf-8"))
    raw["stop_mappings"] = {"60000": {"exits": ["bif-moncasi"]}}
    with pytest.raises(ValidationError, match="es un baipás"):
        NetworkSpec.model_validate(raw)
    raw["stop_mappings"] = {}
    raw["line"]["bypass_of"] = raw["line"]["id"]
    with pytest.raises(ValidationError, match="baipás de sí misma"):
        NetworkSpec.model_validate(raw)


def test_bypasses_of_measures_them_on_the_line(
    bcn: BuiltNetwork, zaragoza: BuiltNetwork, lleida: BuiltNetwork
) -> None:
    line = loaded_line(bcn)
    found = bypasses_of(line, [loaded_line(lleida), loaded_line(zaragoza)])
    assert [b.pieces[0].segment_id.split(":")[0] for b in found] == [
        "baipas-zaragoza",
        "baipas-lleida",
    ]
    first, second = found
    assert (first.km_from, first.km_to) == pytest.approx((294.7, 320.3), abs=0.05)
    assert (first.length_km, first.saved_km) == pytest.approx((20.7, 4.9), abs=0.05)
    assert (second.length_km, second.saved_km) == pytest.approx((14.3, 2.0), abs=0.05)
    assert first.note == "No para en Zaragoza-Delicias: por eso va por aquí."
    assert second.note == "No para en Lleida-Pirineus: por eso va por aquí."
    assert all(p.same_direction for b in found for p in b.pieces)
    # otra línea no los tiene, y un baipás cuyos extremos no están en la línea no se puede seguir
    seville = loaded_line(build_network(load_network_spec(SPEC), DATA_DIR))
    assert bypasses_of(seville, [loaded_line(zaragoza)]) == []
    stray = LoadedLine(
        zaragoza.spec.model_copy(deep=True),
        loaded_line(zaragoza).nodes,
        loaded_line(zaragoza).segments,
    )
    stray.spec.line.bypass_of = "lav-madrid-sevilla"
    assert bypasses_of(seville, [stray]) == []


def test_validate_counts_the_trains_of_each_bypass(tmp_path: Path) -> None:
    """En el fichero del 8 de noviembre de 2026, 97 viajes de Renfe no paran en Zaragoza y 224 no
    paran en Lleida; de los 25 de Ouigo, 10 y los 25. Todos son AVE o trenes de Ouigo, y todos sus
    pasos son estimados: una bifurcación no es una parada."""
    others = [BCN_SPEC, BYPASS_ZARAGOZA_SPEC, BYPASS_LLEIDA_SPEC]
    expected = {
        BYPASS_ZARAGOZA_SPEC: ({"AVE": 97}, {"TGV": 10}),
        BYPASS_LLEIDA_SPEC: ({"AVE": 169, "AVE INT": 55}, {"TGV": 25}),
    }
    for path, (renfe, ouigo) in expected.items():
        report = validate_all(path, FEED, DATA_DIR, others)
        assert report["problems"] == []
        assert report["gtfs"]["products"] == renfe
        assert report["gtfs"]["passes"] == {"estimado": sum(renfe.values())}
        assert report["gtfs"]["resolution"] == {"completa": sum(renfe.values())}
        report = validate_all(
            path, OUIGO_FEED, DATA_DIR, others, stop_id_prefix=OUIGO_STOP_ID_PREFIX
        )
        assert report["problems"] == [] and report["gtfs"]["products"] == ouigo
    # la línea ya no cuenta esos pasos en los tramos de las estaciones: 7.590 − 2 × 97 − 224
    main = validate_all(BCN_SPEC, FEED, DATA_DIR, others, require_rules=False)
    assert main["gtfs"]["trips"] == 571 and main["gtfs"]["passes"] == {"estimado": 6851}
    assert 6851 + 97 + 224 == 7590 - 2 * 97 - 224
    # sin la línea de la que es baipás, o con un extremo que no es nodo suyo, validate lo dice
    alone = validate_all(BYPASS_ZARAGOZA_SPEC, FEED, DATA_DIR, [])
    assert alone["problems"] == [f"es un baipás de {BCN}, que no está entre las líneas cargadas"]
    assert alone["gtfs"]["trips"] == 0
    raw = json.loads(BYPASS_ZARAGOZA_SPEC.read_text(encoding="utf-8"))
    raw["line"]["bypass_of"] = "lav-madrid-sevilla"
    wrong = tmp_path / "baipas-zaragoza.json"
    wrong.write_text(json.dumps(raw), encoding="utf-8")
    report = validate_all(wrong, FEED, DATA_DIR, [SPEC])
    assert report["problems"] == [
        "es un baipás de lav-madrid-sevilla, pero bif-moncasi y bif-canal-imperial no son nodos suyos"
    ]
