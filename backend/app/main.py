"""FastAPI application: API, inbound webhooks, the demo APIs and the scheduler."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, credentials, integrations, runs, system
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.db.session import init_db
from app.demo import api as demo_api

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
logger = logging.getLogger("databridge")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    task = None
    if settings.scheduler_enabled:
        from app.scheduler.loop import run_forever

        task = asyncio.create_task(run_forever(settings.scheduler_tick_seconds))
    logger.info("DataBridge ready (scheduler=%s)", settings.scheduler_enabled)
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="DataBridge API",
    description="Sync records between REST APIs and webhooks: fetch, map, transform, deliver — with retries and run logs.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
install_error_handlers(app)
for router in (system.router, auth.router, credentials.router, integrations.router, runs.router, demo_api.router):
    app.include_router(router)


@app.get("/", include_in_schema=False)
def index() -> JSONResponse:
    return JSONResponse({"service": "databridge-api", "docs": "/docs"})
