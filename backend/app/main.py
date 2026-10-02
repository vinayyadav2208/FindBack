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
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.migrations import ensure_schema
from app.routers import (
    admin,
    auth,
    claims,
    donations,
    found_items,
    home,
    lost_items,
    matches,
    notifications,
    reports,
    search,
    uploads,
)

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
    settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
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

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces or internals to clients (§40).
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Registration order: first added = innermost.  Logging is registered by the
# decorator above, then RateLimit, then CORS (so 429 responses still carry
# Access-Control-Allow-Origin), and SecurityHeaders last so it is outermost
# and covers every response, including preflights and 429s.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Let browser JS read rate-limit feedback on 429 responses.
    expose_headers=["Retry-After", "X-RateLimit-Limit"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(home.router)
app.include_router(auth.router)
app.include_router(lost_items.router)
app.include_router(found_items.router)
app.include_router(donations.router)
app.include_router(claims.router)
app.include_router(search.router)
app.include_router(matches.router)
app.include_router(uploads.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(admin.router)

# Uploaded images are served back to the frontend from here.
settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.MEDIA_DIR)), name="media")
