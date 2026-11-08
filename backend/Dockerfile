# API e importador de Oniel. La misma imagen sirve para el servicio web y para el job de importación.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-install-project

COPY src ./src
COPY data ./data
COPY docker-entrypoint.sh ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked

ENV PATH="/app/.venv/bin:$PATH" PORT=8000
EXPOSE 8000
# Con ONIEL_IMPORT_ON_START=1 el arranque importa los datos antes de servir (ver docker-entrypoint.sh).
CMD ["./docker-entrypoint.sh"]
