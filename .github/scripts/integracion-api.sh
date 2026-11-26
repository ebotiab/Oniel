#!/usr/bin/env bash
# La base debe ser efímera y exclusiva de este trabajo; nunca se usa el .env para elegirla.
set -euo pipefail
cd "$(dirname "$0")/../.."
raiz="$PWD"
: "${ONIEL_DATABASE_URL:?Indica la base PostgreSQL efímera oniel_integracion}"
backend/.venv/bin/python - <<'PY'
import os
from urllib.parse import urlparse

url = urlparse(os.environ['ONIEL_DATABASE_URL'])
if url.scheme != 'postgresql' or url.hostname not in {'127.0.0.1', 'localhost'} or url.path != '/oniel_integracion':
    raise SystemExit('La integración exige PostgreSQL local y la base exclusiva oniel_integracion.')
PY
registros="${RUNNER_TEMP:-/tmp}/oniel-integracion"
mkdir -p "$registros"
credenciales=$(mktemp -d)
export LOGFIRE_CREDENTIALS_DIR="$credenciales"
export LOGFIRE_TOKEN='' VITE_LOGFIRE_TOKEN='' LOGFIRE_SEND_TO_LOGFIRE=false
export ONIEL_ENVIRONMENT=ci
unset ONIEL_E2E_STATIC VERCEL_ENV
export ONIEL_API_PROXY="http://127.0.0.1:${ONIEL_INTEGRACION_API_PORT:-8010}"
export PLAYWRIGHT_JSON_OUTPUT_FILE="$registros/playwright.json"
api_pid=''
# Se compara el contenido, también en local con cambios aún sin confirmar.
git diff --binary HEAD | sha256sum > "$registros/versionados-antes.sha256"
limpiar() {
  resultado=$?
  trap - EXIT
  cd "$raiz"
  if [ -n "$api_pid" ]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  rm -rf "$credenciales"
  git diff --binary HEAD | sha256sum > "$registros/versionados-despues.sha256"
  if ! cmp -s "$registros/versionados-antes.sha256" "$registros/versionados-despues.sha256"; then
    echo '::error::La preparación o las pruebas han modificado archivos versionados.'
    resultado=1
  fi
  exit "$resultado"
}
trap limpiar EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Crea tablas e importa todos los datos del repositorio sin reescribir la instantánea.
(cd backend && timeout --kill-after=5s 4m uv run --locked oniel-data import all --no-snapshot) > "$registros/importacion.log" 2>&1
(cd backend && exec timeout --kill-after=5s 6m .venv/bin/uvicorn oniel.api.main:app --host 127.0.0.1 --port "${ONIEL_INTEGRACION_API_PORT:-8010}" --timeout-graceful-shutdown 5) > "$registros/api.log" 2>&1 &
api_pid=$!
# /healthz solo se alcanza una vez abierto el pool; espera acotada y detecta también un proceso muerto.
lista=false
for ((intento=0; intento<30; intento++)); do
  kill -0 "$api_pid" 2>/dev/null || { cat "$registros/api.log"; exit 1; }
  if curl --fail --silent --show-error --connect-timeout 1 --max-time 2 "$ONIEL_API_PROXY/healthz" > "$registros/salud.json" 2>/dev/null; then
    lista=true
    break
  fi
  sleep 1
done
[ "$lista" = true ] || { echo '::error::La API local no arrancó a tiempo.'; cat "$registros/api.log"; exit 1; }

cd frontend
timeout --kill-after=10s 6m npx playwright test --config ../.github/scripts/playwright-integracion.config.mts --reporter=list,json
# No basta con verde si accidentalmente se han omitido los casos que este trabajo debe cubrir.
node --input-type=module - <<'JS'
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
const informe = JSON.parse(readFileSync(process.env.PLAYWRIGHT_JSON_OUTPUT_FILE, 'utf8'))
assert.equal(informe.stats.skipped, 0, 'La integración no puede omitir pruebas')
assert.ok(informe.stats.expected > 0, 'La integración debe ejecutar casos con API')
JS
cd "$raiz"
