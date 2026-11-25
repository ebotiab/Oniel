"""Rótulos de tren y nombres de estación: los mismos en las listas y en las descripciones (#263)."""

from typing import Any

from conftest import DATA_DIR, FEED, SOURCES, SPECS

from oniel.gtfs.reader import PRODUCT_NAMES, STOP_NAMES, GtfsFeed, feed_products, product_name
from oniel.network.spec import load_feeds
from oniel.validate import cited_products, validate_products

VIGENTE = DATA_DIR / "raw" / "renfe" / "google_transit_av_ld_md_2026-11-17.zip"


def test_cada_tipo_de_tren_tiene_una_sola_escritura() -> None:
    assert product_name("AVANT") == "Avant"
    assert product_name("AVANT EXP") == "Avant Exprés"
    assert product_name("REG.EXP.") == "Regional Exprés"
    assert product_name("REGIONAL") == product_name("Regional") == "Regional"
    # lo que no está en la tabla se deja como viene: no se cambia un tipo por otro
    assert product_name("Intercity") == "Intercity"
    assert product_name("AVE Euromed") == "AVE Euromed"
    # ninguna escritura sigue en mayúsculas ni abreviada, salvo las siglas
    assert all(not v.isupper() and "." not in v for v in PRODUCT_NAMES.values())


def test_el_lector_rotula_los_trenes_con_la_escritura_unica(feed: GtfsFeed) -> None:
    products = {t.product for t in feed.trips.values()}
    assert not products & set(PRODUCT_NAMES)
    assert {"Avant", "Media Distancia", "Regional Exprés", "Alvia", "Proximidad"} <= products


def test_los_rotulos_del_fichero_del_17_de_noviembre() -> None:
    # El fichero que hizo cambiar las descripciones: ya no rotula Alvia ni Media Distancia.
    assert feed_products(VIGENTE) == {
        "AVE",
        "AVE Euromed",
        "AVLO",
        "Avant",
        "Avant Exprés",
        "Intercity",
        "Regional",
    }
    assert "Alvia" in feed_products(FEED)


def test_los_nombres_corregidos_son_de_paradas_del_fichero(feed: GtfsFeed) -> None:
    for stop_id, name in STOP_NAMES.items():
        assert feed.stops[stop_id].name == name
    assert feed.stops["11600"].name == "Irún"


def test_un_texto_cita_los_tipos_de_tren_por_su_rotulo() -> None:
    known = ["Alvia", "Intercity", "Regional", "Regional Exprés", "Media Distancia", "Proximidad"]
    assert cited_products("Paran los Alvia e Intercity y los Regional Exprés.", known) == [
        "Alvia",
        "Intercity",
        "Regional Exprés",
    ]
    # las palabras corrientes, en minúscula, no son el tipo de tren
    assert cited_products("trenes regionales y de media distancia, por su proximidad", known) == []


def test_las_descripciones_nombran_los_trenes_como_los_ficheros_vigentes() -> None:
    report = validate_products(SPECS, load_feeds(SOURCES), DATA_DIR)
    assert report["problems"] == []
    assert {"Intercity", "Regional", "Avant", "Ouigo", "Iryo"} <= set(report["products"])
    assert "Alvia" not in report["products"]


def test_una_descripcion_con_un_rotulo_que_ya_no_viene_no_pasa(tmp_path: Any) -> None:
    spec = next(p for p in SPECS if p.name == "sevilla-huelva.json")
    text = spec.read_text(encoding="utf-8")
    assert "los Intercity de Madrid a Huelva" in text
    stale = tmp_path / spec.name
    stale.write_text(
        text.replace("los Intercity de Madrid a Huelva", "los Alvia de Madrid a Huelva"),
        encoding="utf-8",
    )
    report = validate_products([stale], load_feeds(SOURCES), DATA_DIR)
    assert report["problems"] and all("Alvia" in p for p in report["problems"])
