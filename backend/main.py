"""FastAPI app entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import supabase_admin
from routers import admin as admin_router
from routers import billing as billing_router
from routers import vapi as vapi_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

if settings.SENTRY_DSN_BACKEND:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN_BACKEND,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.0,
        send_default_pii=False,
        environment="production",
    )
    logger.info("Sentry initialized")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the embedding model during container boot so the first live
    # call doesn't pay the ~10-12 second cold-start cost. Vapi times out
    # well before that and the caller hears silence. Railway's healthcheck
    # waits on this, which is the right behavior — don't accept traffic
    # until we can actually answer it.
    try:
        from services.embedding import get_model

        logger.info("Warming sentence-transformers model...")
        get_model().encode("warmup", normalize_embeddings=True)
        logger.info("Embedding model warm.")
    except Exception as exc:
        logger.warning("Embedding warmup failed (will retry on first call): %s", exc)
    yield


app = FastAPI(title="CareCall AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    # Vercel issues a fresh subdomain on every deploy (frontend-<hash>-...
    # .vercel.app), and the carecallai.ca apex / subdomains will eventually
    # serve the prod app. Match the whole family so preflight stops failing
    # on URLs that aren't the static alias.
    allow_origin_regex=r"https://([a-z0-9-]+\.)*vercel\.app|https://([a-z0-9-]+\.)*carecallai\.ca",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vapi_router.router)
app.include_router(admin_router.router)
app.include_router(billing_router.router)


@app.get("/health")
def health() -> dict:
    db_ok = False
    try:
        supabase_admin().table("clinics").select("id").limit(1).execute()
        db_ok = True
    except Exception as exc:
        logger.warning("Health DB ping failed: %s", exc)
    return {"status": "ok", "db": db_ok}
