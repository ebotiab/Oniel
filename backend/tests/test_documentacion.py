"""Los recuentos que la documentación da en palabras coinciden con las especificaciones cargadas.

`CLAUDE.md` y `docs/datos.md` dicen cuántas líneas, baipases y enlaces hay, y cuántas zonas. Cada
línea nueva los deja atrás si nadie los toca: estas pruebas fallan entonces y dicen qué frase falta.
"""

from __future__ import annotations

import json
import re
from typing import Any

from conftest import DATA_DIR

CURATED = DATA_DIR / "curated"
RAIZ = DATA_DIR.parents[1]
CLAUDE = RAIZ / "CLAUDE.md"
DATOS = RAIZ / "docs" / "datos.md"

_HASTA_29 = [
    "cero",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "once",
    "doce",
    "trece",
    "catorce",
    "quince",
    "dieciséis",
    "diecisiete",
    "dieciocho",
    "diecinueve",
    "veinte",
    "veintiuno",
    "veintidós",
    "veintitrés",
    "veinticuatro",
    "veinticinco",
    "veintiséis",
    "veintisiete",
    "veintiocho",
    "veintinueve",
]
_DECENAS = {
    3: "treinta",
    4: "cuarenta",
    5: "cincuenta",
    6: "sesenta",
    7: "setenta",
    8: "ochenta",
    9: "noventa",
}


def en_palabras(n: int, *, femenino: bool = False) -> str:
    """Un número de 0 a 99 como se escribe en la documentación: «treinta y ocho», «veintiuna»."""
    if not 0 <= n <= 99:
        raise ValueError(f"fuera de lo que la documentación escribe en palabras: {n}")
    if n < 30:
        palabra = _HASTA_29[n]
    else:
        decenas, unidades = divmod(n, 10)
        palabra = _DECENAS[decenas] + (f" y {_HASTA_29[unidades]}" if unidades else "")
    if femenino and n % 10 == 1 and n != 11:
        palabra = palabra.removesuffix("uno").removesuffix("ún") + "una"
    return palabra


def _lineas() -> list[dict[str, Any]]:
    """El bloque `line` de cada especificación de `backend/data/curated/`."""
    lineas = []
    for ruta in sorted(CURATED.glob("*.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if isinstance(datos, dict) and "line" in datos:
            lineas.append(datos["line"])
    return lineas


def _recuento() -> tuple[int, int, int]:
    """Cuántas líneas, baipases y enlaces hay: un baipás declara `bypass_of`; un enlace, `link_of`."""
    lineas = _lineas()
    baipases = sum(1 for linea in lineas if linea.get("bypass_of"))
    enlaces = sum(1 for linea in lineas if linea.get("link_of"))
    return len(lineas) - baipases - enlaces, baipases, enlaces


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def test_en_palabras() -> None:
    assert en_palabras(2) == "dos"
    assert en_palabras(1, femenino=True) == "una"
    assert en_palabras(21, femenino=True) == "veintiuna"
    assert en_palabras(38) == "treinta y ocho"
    assert en_palabras(41, femenino=True) == "cuarenta y una"
    assert en_palabras(40) == "cuarenta"


def test_claude_md_dice_cuantas_lineas_baipases_y_enlaces_hay() -> None:
    lineas, baipases, enlaces = _recuento()
    texto = CLAUDE.read_text(encoding="utf-8")
    encontrado = re.search(
        r"Hoy carga ([^,(]+?) líneas?, ([^,(]+?) baipases?, [^(]*? y ([^,(]+?) enlaces?,", texto
    )
    assert encontrado, "CLAUDE.md ya no dice «Hoy carga … líneas, … baipases, …, y … enlace, …»"
    esperado = (
        en_palabras(lineas, femenino=True),
        en_palabras(baipases),
        "un" if enlaces == 1 else en_palabras(enlaces),
    )
    assert encontrado.groups() == esperado, (
        f"CLAUDE.md dice {encontrado.groups()} y las especificaciones de backend/data/curated son {esperado}"
    )


def test_datos_md_dice_cuantas_especificaciones_hay() -> None:
    lineas, baipases, enlaces = _recuento()
    frase = (
        f"Son {lineas + baipases + enlaces} especificaciones: {lineas} {_plural(lineas, 'línea', 'líneas')}, "
        f"{baipases} {_plural(baipases, 'baipás', 'baipases')} y {enlaces} {_plural(enlaces, 'enlace', 'enlaces')}."
    )
    assert frase in DATOS.read_text(encoding="utf-8"), (
        f"docs/datos.md, «Líneas cargadas», tendría que decir: {frase}"
    )


def test_la_tabla_de_lineas_cargadas_tiene_una_fila_por_especificacion() -> None:
    texto = DATOS.read_text(encoding="utf-8")
    apartado = texto.split("\n## Líneas cargadas\n", 1)[1].split("\n## ", 1)[0]
    filas = re.findall(r"^\|[^|]+\| `([a-z0-9-]+)` \|", apartado, flags=re.MULTILINE)
    assert len(filas) == len(set(filas)), "hay una línea repetida en la tabla de «Líneas cargadas»"
    assert set(filas) == {linea["id"] for linea in _lineas()}


def test_datos_md_dice_cuantas_zonas_hay_y_cuantas_tienen_lineas() -> None:
    zonas = json.loads((CURATED / "zonas.json").read_text(encoding="utf-8"))["zones"]
    con_lineas = {linea["zone"] for linea in _lineas()}
    assert con_lineas <= {zona["id"] for zona in zonas}
    apartado = DATOS.read_text(encoding="utf-8").split("\n## Zonas\n", 1)[1].split("\n## ", 1)[0]

    registro = f"`backend/data/curated/zonas.json`: {en_palabras(len(zonas), femenino=True)} zonas,"
    assert registro in apartado, f"docs/datos.md, «Zonas», tendría que decir: {registro}"

    todas = en_palabras(len(zonas), femenino=True)
    if len(con_lineas) == len(zonas):
        frase = f"Hoy tienen líneas las {todas}"
    else:
        frase = f"Hoy tienen líneas {en_palabras(len(con_lineas), femenino=True)} de las {todas}"
    assert frase in apartado, f"docs/datos.md, «Zonas», tendría que decir: {frase}"
