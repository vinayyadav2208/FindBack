"""FindBack FastAPI application entry point.

Run locally:
    cd backend
    python -m uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.migrations import ensure_schema
from app.routers import auth, claims, donations, found_items, home, lost_items, search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("findback")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Non-destructive schema sync on startup (§57, §91): only ADDs missing
    # tables/columns/indexes; never drops or truncates anything.
    ensure_schema(engine, logger=lambda message: logger.info(message))
    logger.info("Database schema is up to date")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FindBack - AI-powered lost, found, donation & community recovery platform. "
        "All state-changing endpoints require a Bearer token from POST /login or "
        "POST /auth/login."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


app.include_router(home.router)
app.include_router(auth.router)
app.include_router(lost_items.router)
app.include_router(found_items.router)
app.include_router(donations.router)
app.include_router(claims.router)
app.include_router(search.router)
