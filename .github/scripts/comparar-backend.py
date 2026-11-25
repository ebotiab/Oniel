"""Experimento de la PR #298: dos revisiones fijas en el mismo ejecutor de GitHub."""

import difflib
import hashlib
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "evidencias-backend"
REFS = {
    "antes": "407cb1a4e030d0793ac576c719ce667e5374e9d7",
    "despues": "989fe14beb9b1ebe737978fb5d10d1d89cc99804",
}
OUT.mkdir()


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


# El experimento no admite cambios en lo que se prueba ni en cómo se mide la cobertura.
run(
    [
        "git",
        "diff",
        "--exit-code",
        *REFS.values(),
        "--",
        "backend/tests",
        "backend/pyproject.toml",
        "backend/uv.lock",
        ".github/workflows/ci.yml",
        "frontend/public/data",
        "frontend/e2e/fixtures",
        "AGENTS.md",
        "docs/datos.md",
    ]
)
metadata = {
    "refs": REFS,
    "runner": {
        key: os.environ.get(key)
        for key in ["ImageOS", "ImageVersion", "RUNNER_ARCH", "RUNNER_OS"]
    },
    "postgres_image": subprocess.check_output(
        ["docker", "inspect", "--format", "{{.Image}}", os.environ["POSTGRES_ID"]],
        text=True,
    ).strip(),
}
(OUT / "entorno.json").write_text(json.dumps(metadata, indent=2) + "\n")
worktrees = {}
for name, ref in REFS.items():
    tree = Path(os.environ["RUNNER_TEMP"]) / f"oniel-{name}"
    run(["git", "worktree", "add", "--detach", str(tree), ref])
    worktrees[name] = tree
    run(["uv", "sync", "--locked"], cwd=tree / "backend")

times = {}
for name, tree in worktrees.items():
    print(f"::group::Revisión {name}: {REFS[name]}", flush=True)
    folder = OUT / name
    folder.mkdir()
    for worker in range(3):
        db = f"oniel_test_gw{worker}"
        run(
            [
                "docker",
                "exec",
                os.environ["POSTGRES_ID"],
                "dropdb",
                "-U",
                "oniel",
                "--if-exists",
                db,
            ]
        )
        run(
            ["docker", "exec", os.environ["POSTGRES_ID"], "createdb", "-U", "oniel", db]
        )
    env = os.environ | {
        "ONIEL_TEST_DATABASE_URL": "postgresql://oniel@localhost:5432/oniel_test_{worker}",
        "PYTEST_ADDOPTS": "-n 3 --dist=loadfile --max-worker-restart=0",
        "COVERAGE_FILE": str(folder / ".coverage"),
    }
    commands = [
        ("formato", ["uv", "run", "ruff", "format", "--check", "."]),
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("mypy", ["uv", "run", "mypy"]),
        ("pyright", ["uv", "run", "pyright"]),
        (
            "pytest",
            [
                "uv",
                "run",
                "pytest",
                "--cov",
                "--cov-report=term",
                f"--junitxml={folder}/junit.xml",
            ],
        ),
        ("cobertura", ["uv", "run", "coverage", "report", "--format=markdown"]),
        ("validar", ["uv", "run", "oniel-data", "validate"]),
        (
            "json",
            ["uv", "run", "coverage", "json", "-o", str(folder / "coverage.json")],
        ),
    ]
    times[name] = []
    for label, command in commands:
        print(f"{name}: {label}", flush=True)
        start = time.perf_counter()
        with (folder / f"{label}.log").open("w") as log:
            result = subprocess.run(
                command,
                cwd=tree / "backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        record = {
            "command": command,
            "check": label,
            "seconds": time.perf_counter() - start,
            "returncode": result.returncode,
        }
        times[name].append(record)
        (OUT / "tiempos.json").write_text(json.dumps(times, indent=2) + "\n")
        print(json.dumps(record), flush=True)
        if result.returncode:
            print((folder / f"{label}.log").read_text(), flush=True)
            result.check_returncode()
    print((folder / "pytest.log").read_text(), flush=True)
    print("::endgroup::", flush=True)


def cases(name):
    xml = ET.parse(OUT / name / "junit.xml")
    assert not any(xml.findall(f".//{tag}") for tag in ["failure", "error", "skipped"])
    found = Counter(
        (t.attrib["classname"], t.attrib["name"]) for t in xml.findall(".//testcase")
    )
    assert len(found) == 771 and set(found.values()) == {1}
    return found


before_cases, after_cases = cases("antes"), cases("despues")
assert before_cases == after_cases
before, after = [
    json.loads((OUT / name / "coverage.json").read_text()) for name in REFS
]
assert before["meta"]["branch_coverage"] and after["meta"]["branch_coverage"]
assert before["files"].keys() == after["files"].keys()
changed = "src/oniel/routing/graph.py"
assert all(
    before["files"][f] == after["files"][f] for f in before["files"] if f != changed
)
for key in ["missing_lines", "missing_branches", "excluded_lines"]:
    assert before["totals"][key] == after["totals"][key]
for key, extra in [
    ("covered_lines", 1),
    ("num_statements", 1),
    ("covered_branches", 2),
    ("num_branches", 2),
]:
    assert after["totals"][key] == before["totals"][key] + extra
old_lines, new_lines = [
    (tree / "backend" / changed).read_text().splitlines() for tree in worktrees.values()
]
matcher = difflib.SequenceMatcher(
    a=[s.strip() for s in old_lines], b=[s.strip() for s in new_lines], autojunk=False
)
mapping = {
    i + k + 1: j + k + 1
    for i, j, size in matcher.get_matching_blocks()
    for k in range(size)
}
old_graph, new_graph = before["files"][changed], after["files"][changed]
assert {mapping[n] for n in old_graph["missing_lines"]} == set(
    new_graph["missing_lines"]
)
assert all(
    mapping[n] in new_graph["executed_lines"]
    for n in old_graph["executed_lines"]
    if n in mapping
)
summary = {
    **metadata,
    "tests": len(before_cases),
    "test_ids_sha256": digest(sorted(before_cases)),
    "coverage_files": len(before["files"]),
    "unchanged_coverage_files": len(before["files"]) - 1,
    "totals_before": before["totals"],
    "totals_after": after["totals"],
    "seconds": {
        name: {r["check"]: r["seconds"] for r in records}
        for name, records in times.items()
    },
}
(OUT / "comparacion.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2), flush=True)
with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as log:
    log.write("## Comparación en el mismo ejecutor\n\n")
    log.write(
        "771 casos idénticos, aprobados una vez cada uno, sin omisiones. Cobertura con ramas verificada.\n\n"
    )
    log.write(
        "| Comprobación | Antes (s) | Después (s) | Reducción |\n| --- | ---: | ---: | ---: |\n"
    )
    for label in summary["seconds"]["antes"]:
        a, b = (summary["seconds"][name][label] for name in REFS)
        log.write(f"| {label} | {a:.2f} | {b:.2f} | {(1 - b / a) * 100:.1f} % |\n")
