"""El validador comparte la red y los horarios entre informes de una misma ejecución."""

from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import CONV_SPEC, DATA_DIR, SOURCES, SPEC, SPECS
from typer.testing import CliRunner

from oniel import validate
from oniel.cli.main import app
from oniel.network.build import build_network
from oniel.network.spec import load_feeds


def test_cada_linea_se_construye_una_vez_y_cada_horario_se_abre_una_vez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feeds = load_feeds(SOURCES)
    monkeypatch.chdir(SPEC.parent)
    with (
        patch.object(validate, "build_network", wraps=build_network) as build,
        patch.object(zipfile, "ZipFile", wraps=zipfile.ZipFile) as open_zip,
    ):
        result = CliRunner().invoke(
            app, ["validate", "--spec", SPEC.name, "--spec", CONV_SPEC.name]
        )

    assert result.exit_code == 0, result.output
    assert Counter(call.args[0].line.id for call in build.call_args_list) == Counter(
        path.stem for path in SPECS
    )
    assert [Path(call.args[0]) for call in open_zip.call_args_list] == [
        DATA_DIR / feed.file for feed in feeds
    ]
    reports = json.loads(result.output)
    assert [(r["line"], r["gtfs"]["file"]) for r in reports if "gtfs" in r] == [
        (path.stem, Path(feed.file).name) for feed in feeds for path in (SPEC, CONV_SPEC)
    ]
