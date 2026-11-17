#!/bin/sh
# Arranque de la imagen de Oniel.
# Con ONIEL_IMPORT_ON_START=1 ejecuta la importación repetible antes de servir la API, de modo que
# un despliegue sin cron job (plan gratuito de Render) deja la base cargada. `--if-changed` la salta
# cuando el commit desplegado ya está importado: así despertar tras una suspensión no repite la
# importación. `--no-snapshot` no exporta la instantánea estática del visor: esa la sirve Vercel
# desde el repositorio y en este contenedor no la lee nadie (docs/despliegue.md).
set -eu

if [ "${ONIEL_IMPORT_ON_START:-0}" = "1" ]; then
  echo "[oniel] ONIEL_IMPORT_ON_START=1: ejecutando 'oniel-data import all --if-changed --no-snapshot' antes de arrancar la API"
  # Con una lectura de métricas cada 10 s, y no cada minuto, se ve cuánta memoria y procesador
  # usa la importación mientras carga.
  OTEL_METRIC_EXPORT_INTERVAL=10000 oniel-data import all --if-changed --no-snapshot
fi

# uvicorn directamente: la imagen instala solo las dependencias de producción y no incluye la CLI `fastapi`.
exec uvicorn oniel.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
