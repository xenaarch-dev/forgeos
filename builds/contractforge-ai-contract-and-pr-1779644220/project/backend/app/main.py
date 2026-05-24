from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import billing, health, items
from .sentry import init_sentry

logging.basicConfig(level=settings.log_level)
init_sentry()

app = FastAPI(
    title="App API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CRITICAL: never remove these — Render health checks /healthz on every deploy.
@app.get("/")
def root() -> dict:
    return {"app": "App API", "version": "1.0.0", "status": "running"}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


app.include_router(health.router)
app.include_router(items.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
