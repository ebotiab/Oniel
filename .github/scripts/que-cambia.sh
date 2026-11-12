#!/usr/bin/env bash
# Decide qué mitad del CI puede verse afectada por una lista de ficheros cambiados.
#
# Lee una ruta por línea en la entrada estándar y escribe `backend=true|false` y
# `frontend=true|false`, el formato de $GITHUB_OUTPUT. Una mitad solo se salta cuando ningún fichero
# de la lista puede cambiar su resultado; lo que no está clasificado aquí lanza las dos.
#
#   git diff --name-only --no-renames HEAD^1 HEAD | .github/scripts/que-cambia.sh
#
# Por qué cada regla:
# - `docs/`, los `.md` de la raíz, `.vscode/` y `.claude/` no entran en ninguna comprobación, salvo
#   `docs/datos.md`, que leen las pruebas del refresco del GTFS (backend/tests/test_refresh.py).
# - Las pruebas del backend leen la instantánea (`frontend/public/data/`) y los casos de paridad de
#   rutas (`frontend/e2e/fixtures/`); el resto de `frontend/` no las afecta.
# - Playwright prueba en el CI la instantánea estática, sin API: del backend solo le llega lo que
#   esté en `frontend/public/data/`. Aun así, un cambio en los datos curados o crudos o en el
#   exportador lanza también el visor, porque de ahí sale la instantánea.
set -euo pipefail

backend=false
frontend=false
ficheros=0

while IFS= read -r ruta; do
  [ -z "$ruta" ] && continue
  ficheros=$((ficheros + 1))
  case "$ruta" in
    docs/datos.md) backend=true ;;
    docs/* | .vscode/* | .claude/*) ;;
    frontend/public/data/* | frontend/e2e/fixtures/*) backend=true; frontend=true ;;
    frontend/*) frontend=true ;;
    backend/data/* | backend/src/oniel/export/*) backend=true; frontend=true ;;
    backend/*) backend=true ;;
    */*) backend=true; frontend=true ;;
    *.md) ;;
    *) backend=true; frontend=true ;;
  esac
done

# Sin ficheros no hay nada que justifique saltarse una mitad.
if [ "$ficheros" -eq 0 ]; then
  backend=true
  frontend=true
fi

echo "backend=$backend"
echo "frontend=$frontend"
