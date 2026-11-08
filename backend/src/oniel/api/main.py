"""API de Oniel."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oniel import __version__
from oniel.api.routers import network, nodes, segments, services, simulations
from oniel.db.pool import create_pool
from oniel.observability import configure_logfire
from oniel.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.pool = await create_pool(settings.database_url)
    try:
        yield
    finally:
        await app.state.pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logfire("oniel-api", settings)
    app = FastAPI(
        title="Oniel API",
        version=__version__,
        description="Cómo está conectada la red ferroviaria española: red, servicios y simulaciones.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logfire.instrument_fastapi(app, capture_headers=False)

    @app.get("/healthz", tags=["sistema"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    for router in (
        network.router,
        segments.router,
        nodes.router,
        services.router,
        simulations.router,
    ):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
