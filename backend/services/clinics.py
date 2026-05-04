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


# Statuses that allow live AI calls. 'past_due' keeps service running while
# Stripe retries — flip to a hard block by removing it once we have email
# escalation in place.
LIVE_STATUSES = {"trial", "trialing", "active", "pilot", "starter", "past_due"}


def is_clinic_live(clinic_id: str) -> bool:
    """Return True if the clinic's subscription is in a live-call status."""
    try:
        res = (
            supabase_admin()
            .table("clinics")
            .select("subscription_status,is_active")
            .eq("id", clinic_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("subscription status lookup failed for %s: %s", clinic_id, exc)
        return True  # fail-open: don't break a live call on a transient DB hiccup
    if not res.data:
        return False
    row = res.data[0]
    if row.get("is_active") is False:
        return False
    return (row.get("subscription_status") or "trial") in LIVE_STATUSES
