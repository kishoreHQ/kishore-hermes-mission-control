"""Hermes OS API — FastAPI gateway."""

from app.config import settings
from app.db.session import engine
from app.models.base import Base
from app.routers import (
    actions,
    agents,
    ai,
    content,
    dispatch,
    health,
    infrastructure,
    insights,
    nightly,
    plugins,
    status,
    stream,
    system,
    tasks,
    today,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Hermes OS API",
    version="2.0.0",
    description="Personal AI operating system gateway",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(status.router, prefix="/api/v1")
app.include_router(today.router, prefix="/api/v1")
app.include_router(dispatch.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(infrastructure.router, prefix="/api/v1")
app.include_router(nightly.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(plugins.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    if not settings.auto_create_tables:
        return
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger("hermes.api").warning("DB init skipped: %s", exc)
