"""FastAPI app entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import supabase_admin
from routers import admin as admin_router
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

app = FastAPI(title="CareCall AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vapi_router.router)
app.include_router(admin_router.router)


@app.get("/health")
def health() -> dict:
    db_ok = False
    try:
        supabase_admin().table("clinics").select("id").limit(1).execute()
        db_ok = True
    except Exception as exc:
        logger.warning("Health DB ping failed: %s", exc)
    return {"status": "ok", "db": db_ok}
