#!/bin/sh
# Arranque de la imagen de Oniel.
# Con ONIEL_IMPORT_ON_START=1 ejecuta la importación repetible antes de servir la API,
# de modo que un despliegue sin cron job (plan gratuito de Render) deja la base cargada.
set -eu

if [ "${ONIEL_IMPORT_ON_START:-0}" = "1" ]; then
  echo "[oniel] ONIEL_IMPORT_ON_START=1: ejecutando 'oniel-data import all' antes de arrancar la API"
  oniel-data import all
fi

# uvicorn directamente: la imagen instala solo las dependencias de producción y no incluye la CLI `fastapi`.
exec uvicorn oniel.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
