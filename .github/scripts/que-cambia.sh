#!/usr/bin/env bash
# Decide qué bloques del CI puede verse afectada por una lista de ficheros cambiados.
#
# Lee una ruta por línea y escribe `backend`, `frontend` e `integracion` como true|false,
# el formato de $GITHUB_OUTPUT. Un bloque solo se salta cuando ningún fichero de la lista
# puede cambiar su resultado; lo que no está clasificado aquí lanza los tres.
#
#   git diff --name-only --no-renames HEAD^1 HEAD | .github/scripts/que-cambia.sh
#
# Por qué cada regla:
# - `docs/`, los `.md` de la raíz, `.vscode/` y `.claude/` no entran en ninguna comprobación, salvo
#   `docs/datos.md`, que leen las pruebas del refresco del GTFS (backend/tests/test_refresh.py), y
#   `docs/datos.md` y `AGENTS.md`, cuyos recuentos comprueba backend/tests/test_documentacion.py.
# - Las pruebas del backend leen la instantánea (`frontend/public/data/`) y los casos de paridad de
#   rutas (`frontend/e2e/fixtures/`); el resto de `frontend/` no las afecta.
# - Playwright prueba en el CI la instantánea estática, sin API: del backend solo le llega lo que
#   esté en `frontend/public/data/`. Aun así, un cambio en los datos curados o crudos o en el
#   exportador lanza también el visor, porque de ahí sale la instantánea.
# - La integración visor–API depende de todo backend/ y frontend/ (datos, contratos, dependencias
#   y pruebas incluidos). Los cambios sin clasificar, entre ellos el CI, activan los tres bloques.
set -euo pipefail

backend=false
frontend=false
integracion=false
ficheros=0

while IFS= read -r ruta; do
  [ -z "$ruta" ] && continue
  ficheros=$((ficheros + 1))
  case "$ruta" in
    docs/datos.md | AGENTS.md | CLAUDE.md) backend=true ;;
    docs/* | .vscode/* | .claude/* | .agents/skills/* | .codex/environments/*) ;;
    frontend/public/data/* | frontend/e2e/fixtures/*) backend=true; frontend=true; integracion=true ;;
    frontend/*) frontend=true; integracion=true ;;
    backend/data/* | backend/src/oniel/export/*) backend=true; frontend=true; integracion=true ;;
    backend/*) backend=true; integracion=true ;;
    */*) backend=true; frontend=true; integracion=true ;;
    *.md) ;;
    *) backend=true; frontend=true; integracion=true ;;
  esac
done

# Sin ficheros no hay nada que justifique saltarse una mitad.
if [ "$ficheros" -eq 0 ]; then
  backend=true
  frontend=true
  integracion=true
fi

echo "backend=$backend"
echo "frontend=$frontend"
echo "integracion=$integracion"
