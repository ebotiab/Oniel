# Tiempo del CI del backend

El 25 de noviembre de 2026 se comparó `f1d5bbe` con la optimización de `_walk` que cuenta
los cambios de línea solo cuando se pide un límite. El recuento no afecta a los recorridos
sin límite, pero se repetía millones de veces en las búsquedas de desvíos. Los límites de
cero, uno y varios cambios siguen comprobándose en las pruebas existentes.

## Comparación local equivalente

Una ejecución por revisión, consecutivas en la misma máquina Linux con cuatro CPU
asignadas, Python 3.13.5, el mismo `uv.lock`, pytest 9.2.0, pytest-cov 7.1.0 y coverage
7.17.3. En ambas se usó la misma imagen local de PostgreSQL 17 Alpine
(`sha256:fa7e2700e906190f900a3c9d47e87f9032cfa38b60d9ac25129a357f85c2da8c`),
un contenedor recién creado y tres bases vacías. Se ejecutaron los mismos comandos, sin
otras pruebas simultáneas. Los tiempos son de reloj; no incluyen la preparación del
contenedor ni la instalación de dependencias, ya presentes en las dos ejecuciones.

| Medida | Antes | Después | Reducción |
| --- | ---: | ---: | ---: |
| Orden completa de pytest con cobertura | 479,97 s | 399,80 s | 16,7 % |
| Caso que comprueba los desvíos de todos los tramos | 402,44 s | 334,67 s | 16,8 % |
| Formato, lint, tipos, pytest, informe Markdown y validación | 501,50 s | 421,34 s | 16,0 % |

Son mediciones locales de los comandos del CI, no duraciones de un ejecutor de GitHub.
La descripción de la PR recoge por separado las ejecuciones de GitHub Actions. Una sola
pareja no estima la variabilidad entre ejecutores.

## Pruebas y cobertura conservadas

Los XML de JUnit contienen exactamente los mismos **771 pares de clase y nombre de
prueba**, cada uno ejecutado una vez y aprobado, con cero omisiones, errores o fallos.
El SHA-256 de `json.dumps(sorted(pares), ensure_ascii=False).encode()` es
`90992a99ea5df78b8042834a8d8d279c231cb365ce33429cf08614d4ae99f7d3` en ambas ejecuciones.
No se ha editado ningún fichero de pruebas, el flujo de CI, el lockfile ni su configuración.

Ambos informes JSON miden los mismos 55 ficheros de `oniel`, con ramas. El contenido de
`files` coincide por completo en los 54 ficheros no modificados. El SHA-256 de
`json.dumps(files_sin_graph, sort_keys=True, separators=(",", ":")).encode()` es
`baf2574a71dcc34fcb35b89678c8c06d654b7cafd65b69c468d54a6cdd3352c2` en ambos.

| Cobertura | Antes | Después |
| --- | ---: | ---: |
| Sentencias cubiertas / totales | 4.798 / 5.002 | 4.799 / 5.003 |
| Ramas cubiertas / totales | 1.279 / 1.402 | 1.281 / 1.404 |
| Sentencias sin cubrir | 204 | 204 |
| Ramas sin cubrir | 123 | 123 |
| Líneas excluidas | 60 | 60 |
| Porcentaje combinado mostrado | 95 % | 95 % |

La condición añadida aporta una sentencia y dos ramas, todas cubiertas. En
`routing/graph.py` se conserva la cobertura de las líneas comunes y las mismas 16
sentencias sin cubrir, ajustando sus números al desplazamiento del código; siguen
quedando 19 ramas sin cubrir. No se añade ninguna exclusión. El informe sigue siendo
informativo, sin umbral, y en GitHub se genera en `main`, como antes.

En las dos revisiones pasan Ruff (formato y lint), mypy estricto, pyright, las pruebas
con PostgreSQL, `coverage report --format=markdown` y `oniel-data validate`.

## Reproducir la comparación

Preparar un contenedor nuevo de la misma imagen y las bases `oniel_test_gw0`,
`oniel_test_gw1` y `oniel_test_gw2` antes de cada revisión. Desde `backend/`, con las
dependencias del lockfile instaladas, ejecutar las órdenes de `.github/workflows/ci.yml`.
Para conservar las evidencias de pytest, indicar un directorio distinto por revisión:

```bash
export ONIEL_TEST_DATABASE_URL='postgresql://oniel@localhost:55433/oniel_test_{worker}'
export PYTEST_ADDOPTS='-n 3 --dist=loadfile --max-worker-restart=0'
export COVERAGE_FILE="$EVIDENCIAS/.coverage"
uv run pytest --cov --cov-report=term --junitxml="$EVIDENCIAS/junit.xml"
uv run coverage report --format=markdown
uv run coverage json -o "$EVIDENCIAS/coverage.json"
```

Medir cada proceso con un reloj monotónico. Comparar los pares `classname`, `name`
de todos los `testcase` de JUnit, comprobar que no haya repeticiones ni elementos
`skipped`, `failure` o `error`, y comparar `files` de ambos JSON de cobertura. En el
único módulo modificado hay que tener en cuenta las líneas desplazadas y la nueva
condición; comparar solo el porcentaje redondeado ocultaría pérdidas pequeñas.
