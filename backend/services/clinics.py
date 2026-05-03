"""Clinic lookups by Vapi identifiers."""
from __future__ import annotations

import logging
from functools import lru_cache

from db import supabase_admin

logger = logging.getLogger(__name__)


def clinic_id_for_assistant(vapi_assistant_id: str | None) -> str | None:
    """Resolve a Vapi assistant id to its clinic_id, or None if unknown."""
    if not vapi_assistant_id:
        return None
    return _cached_clinic_id(vapi_assistant_id)


@lru_cache(maxsize=128)
def _cached_clinic_id(vapi_assistant_id: str) -> str | None:
    try:
        res = (
            supabase_admin()
            .table("clinics")
            .select("id")
            .eq("vapi_assistant_id", vapi_assistant_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("clinic lookup failed for assistant=%s: %s", vapi_assistant_id, exc)
        return None
    if not res.data:
        return None
    return res.data[0]["id"]
